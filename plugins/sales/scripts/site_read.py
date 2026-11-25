#!/usr/bin/env python3
"""site_read.py: read a company website fast and extract plain facts. No scoring, no AI.

Used for three jobs:
  - onboarding: read YOUR site so Claude can draft your ICP and personas;
  - account enrichment: what a prospect sells, to whom, where, how big;
  - finding people: team / about pages often list names and roles.

It fetches the homepage plus the most informative pages (about, offer, customers,
industries, team, contact, pricing, careers), 4 at a time, and writes:

  .tmp/sites/<domain>/pages.json   text of every page, with its URL and kind
  .tmp/sites/<domain>/facts.json   facts found by rule: title, headline, description,
                                   languages, company LinkedIn and social links, emails,
                                   phones, schema.org organisation data, page kinds found
  .tmp/sites/<domain>/logo.<ext>   the company's own logo or icon, if the site has one

Claude reads both and does the judgment (what they sell, who buys, fit).
Pages built only by JavaScript look empty to this script; the facts say so.

    python3 site_read.py example.com [--max-pages 10] [--budget 60] [--out .tmp/sites]
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urldefrag, urlparse

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
KINDS = [  # (kind, url/link-text pattern), most informative first
    ("about", r"about|ueber|über|who-we-are|company|story|unternehmen"),
    ("offer", r"product|service|solution|offer|leistung|angebot|what-we-do|platform|features?"),
    ("customers", r"case|stud|customer|client|referen|success|testimonial|portfolio|\bwork\b|our-work"),
    ("industries", r"industr|sector|branche|market|use-case|who-we-serve"),
    ("team", r"team|people|leadership|management|founders?|mitarbeit|kontaktpersonen"),
    ("contact", r"contact|kontakt|location|standort|impressum|imprint"),
    ("pricing", r"pric|plans?|tarif|preise|packages?"),
    ("careers", r"career|jobs|karriere|join-us|stellen|vacanc"),
]
BOT_WALL = re.compile(r"just a moment|checking your browser|one moment, please|attention required|access denied|captcha", re.I)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SOCIAL = re.compile(r"https?://(?:[a-z]{2,3}\.)?(linkedin\.com/company/[^/?#\"']+|linkedin\.com/in/[^/?#\"']+|x\.com/[^/?#\"']+|"
                    r"twitter\.com/[^/?#\"']+|youtube\.com/[^?#\"']+|instagram\.com/[^/?#\"']+|facebook\.com/[^/?#\"']+)", re.I)


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.desc, self.lang, self.site_name = "", "", "", ""
        self.icons = []  # <link rel="icon" / "apple-touch-icon" ...>
        self.h1, self.links, self.ldjson, self.text = [], [], [], []
        self._skip, self._in, self._a = 0, None, None

    def handle_starttag(self, tag, attrs):
        at = dict(attrs)
        if tag in ("script", "style", "noscript", "svg"):
            self._skip += 1
            if tag == "script" and (at.get("type") or "").lower() == "application/ld+json":
                self._in = "ldjson"
        elif tag == "html":
            self.lang = at.get("lang", "")
        elif tag == "title":
            self._in = "title"
        elif tag == "h1":
            self._in = "h1"
            self.h1.append("")
        elif tag == "meta":
            n = (at.get("name") or at.get("property") or "").lower()
            if n in ("description", "og:description") and not self.desc:
                self.desc = at.get("content", "") or ""
            elif n == "og:site_name" and not self.site_name:
                self.site_name = (at.get("content") or "").strip()
        elif tag == "a" and at.get("href"):
            self._a = {"href": at["href"], "text": ""}
        elif tag == "link":
            rel = str(at.get("rel") or "").lower()
            if "alternate" in rel and at.get("hreflang"):
                self.links.append({"href": at.get("href", ""), "text": "", "hreflang": at["hreflang"]})
            elif "icon" in rel and "mask-icon" not in rel and at.get("href"):
                self.icons.append({"rel": rel, "href": at["href"], "sizes": at.get("sizes") or ""})
        elif tag in ("br", "p", "li", "div", "section", "h2", "h3", "tr"):
            self.text.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg"):
            self._skip = max(0, self._skip - 1)
            if tag == "script" and self._in == "ldjson":
                self._in = None
        elif tag in ("title", "h1"):
            self._in = None
        elif tag == "a" and self._a:
            self.links.append(self._a)
            self._a = None

    def handle_data(self, data):
        if self._in == "ldjson":
            self.ldjson.append(data)
            return
        if self._skip:
            return
        if self._in == "title":
            self.title += data
        elif self._in == "h1":
            self.h1[-1] += data
        if self._a is not None:
            self._a["text"] += data
        self.text.append(data)


def fetch(url: str, timeout: float = 12.0):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*;q=0.8",
                                               "Accept-Language": "en,de;q=0.8,fr;q=0.6"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r:
            body = r.read(2_500_000)
            ctype = r.headers.get("Content-Type", "")
            enc = r.headers.get_content_charset() or "utf-8"
            return {"url": r.geturl(), "status": r.status, "ms": int((time.time() - t0) * 1000),
                    "html": body.decode(enc, "replace") if "html" in ctype or not ctype else ""}
    except urllib.error.HTTPError as e:
        return {"url": url, "status": e.code, "ms": int((time.time() - t0) * 1000), "html": "", "error": f"HTTP {e.code}"}
    except Exception as e:  # noqa: BLE001 - report any network failure as data
        return {"url": url, "status": 0, "ms": int((time.time() - t0) * 1000), "html": "", "error": str(e)[:120]}


def parse(html_text: str) -> Page:
    p = Page()
    try:
        p.feed(html_text)
    except Exception:  # noqa: BLE001 - broken HTML still gives partial data
        pass
    return p


def clean_text(p: Page) -> str:
    t = re.sub(r"[ \t\r\f\v]+", " ", "".join(p.text))
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def kind_of(url: str, text: str) -> str | None:
    s = (urlparse(url).path + " " + urlparse(url).fragment + " " + text).lower()
    for kind, pat in KINDS:
        if re.search(pat, s):
            return kind
    return None


def org_data(pages) -> dict:
    """schema.org Organization-like objects: name, address, employees, sameAs, phone, email."""
    out = {}
    for p in pages:
        for blob in p["parsed"].ldjson:
            try:
                data = json.loads(blob)
            except ValueError:
                continue
            stack = data if isinstance(data, list) else [data]
            while stack:
                x = stack.pop()
                if isinstance(x, list):
                    stack += x
                    continue
                if not isinstance(x, dict):
                    continue
                stack += [v for v in x.values() if isinstance(v, (dict, list))]
                t = x.get("@type")
                types = t if isinstance(t, list) else [t]
                if any(str(tt) in ("Organization", "Corporation", "LocalBusiness", "Company", "ProfessionalService")
                       for tt in types):
                    for k in ("name", "legalName", "description", "url", "logo", "telephone", "email", "foundingDate",
                              "numberOfEmployees", "address", "sameAs", "areaServed"):
                        if x.get(k) and k not in out:
                            out[k] = x[k]
    return out


IMAGE_MAGIC = [(b"\x89PNG", "png"), (b"\xff\xd8", "jpg"), (b"GIF8", "gif"), (b"\x00\x00\x01\x00", "ico")]


def image_ext(data: bytes) -> str | None:
    """File type from the first bytes, so a 404 page saved as 'logo.png' is never kept."""
    for magic, ext in IMAGE_MAGIC:
        if data.startswith(magic):
            return ext
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if b"<svg" in data[:2000].lower():
        return "svg"
    return None


def fetch_bytes(url: str, timeout: float = 8.0) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "image/*,*/*;q=0.5"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r:
            return r.read(1_000_001)
    except Exception:  # noqa: BLE001 - a missing logo is not an error
        return None


def icon_size(icon: dict) -> int:
    m = re.search(r"(\d+)x\d+", icon.get("sizes") or "")
    if m:
        return int(m.group(1))
    return 180 if "apple-touch-icon" in icon["rel"] else (512 if icon["href"].lower().endswith(".svg") else 32)


def save_logo(base: str, hp: Page, org: dict, out: Path) -> dict:
    """Save the company's own logo next to the facts: the biggest square icon first (it looks
    best small), then the schema.org logo, then /favicon.ico. Only real images are kept."""
    cands = [urljoin(base, i["href"]) for i in sorted(hp.icons, key=icon_size, reverse=True) if icon_size(i) >= 64]
    logo = org.get("logo")
    if isinstance(logo, dict):
        logo = logo.get("url") or logo.get("contentUrl")
    if isinstance(logo, str) and logo:
        cands.append(urljoin(base, logo))
    cands += [urljoin(base, i["href"]) for i in hp.icons]
    cands += [urljoin(base, "/apple-touch-icon.png"), urljoin(base, "/favicon.ico")]
    for old in out.glob("logo.*"):
        old.unlink()
    seen = set()
    for url in cands:
        if url in seen or not url.startswith(("http://", "https://")):
            continue
        seen.add(url)
        data = fetch_bytes(url)
        ext = image_ext(data) if data and 100 < len(data) <= 1_000_000 else None
        if ext:
            (out / f"logo.{ext}").write_bytes(data)
            return {"logo_file": f"logo.{ext}", "logo_source": url}
    return {"logo_file": None, "logo_source": None}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("domain")
    ap.add_argument("--max-pages", type=int, default=10)
    ap.add_argument("--budget", type=int, default=60, help="seconds for the whole read")
    ap.add_argument("--out", default=".tmp/sites")
    a = ap.parse_args()

    dom = re.sub(r"^https?://", "", a.domain.strip().lower()).split("/")[0]
    dom = re.sub(r"^www\.", "", dom)
    start = time.time()
    out = Path(a.out) / dom
    out.mkdir(parents=True, exist_ok=True)
    print(f"[read] {dom}: opening the homepage ...", flush=True)
    home = fetch(f"https://{dom}/")
    if home.get("error") and not home["html"]:
        home = fetch(f"https://www.{dom}/")
    hp = parse(home["html"])
    if not home["html"] or BOT_WALL.search(hp.title or "") or BOT_WALL.search(clean_text(hp)[:400]):
        why = home.get("error") or ("bot protection page" if home["html"] else "empty response")
        print(f"[read] the site could not be read automatically ({why}).")
        (out / "facts.json").write_text(json.dumps({"domain": dom, "readable": False, "reason": why}, indent=2))
        sys.exit(2)
    base = home["url"]
    host = urlparse(base).netloc
    print(f"[read] homepage: '{(hp.title or '').strip()[:70]}'", flush=True)

    cands, seen = {}, {urldefrag(base)[0].rstrip("/")}
    for ln in hp.links:
        u = urldefrag(urljoin(base, ln["href"]))[0].rstrip("/")
        if urlparse(u).netloc != host or u in seen or re.search(r"\.(pdf|jpg|png|zip|svg|webp|mp4)$|mailto:|tel:", u, re.I):
            continue
        k = kind_of(u, ln.get("text", ""))
        if k:
            cands.setdefault(k, []).append(u)
            seen.add(u)
    queue = []
    for i in range(3):  # round-robin so every kind of page gets a turn
        for k, _ in KINDS:
            if len(cands.get(k, [])) > i:
                queue.append((k, cands[k][i]))
    queue = queue[: a.max_pages - 1]
    pages = [{"url": base, "kind": "home", "parsed": hp}]
    remaining = max(5.0, a.budget - (time.time() - start))
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(fetch, u, min(15.0, remaining)): (k, u) for k, u in queue}
        for fut in as_completed(futs):
            k, u = futs[fut]
            r = fut.result()
            if not r["html"]:
                print(f"[read]   skip {k:<10} {u} ({r.get('error', 'no html')})", flush=True)
                continue
            pages.append({"url": r["url"], "kind": k, "parsed": parse(r["html"])})
            print(f"[read]   {k:<10} {r['url']}", flush=True)

    raw_links = [ln["href"] for p in pages for ln in p["parsed"].links]
    texts = {p["url"]: clean_text(p["parsed"]) for p in pages}
    emails = sorted({e.lower() for e in EMAIL.findall(" ".join(raw_links) + " " + " ".join(texts.values()))
                     if not re.search(r"\.(png|jpg|gif|webp|svg)$|example\.|sentry|wixpress", e, re.I)})[:10]
    phones = sorted({re.sub(r"[^\d+]", "", h[4:]) for h in raw_links if h.lower().startswith("tel:")})[:5]
    social = sorted({m.group(0).rstrip("/") for h in raw_links for m in [SOCIAL.match(h)] if m})[:12]
    langs = sorted({p["parsed"].lang.split("-")[0].lower() for p in pages if p["parsed"].lang}
                   | {ln["hreflang"].split("-")[0].lower() for ln in hp.links if ln.get("hreflang")} - {"x"})
    thin = [p["url"] for p in pages if len(texts[p["url"]].split()) < 60]
    facts = {
        "domain": dom, "readable": True, "read_at": time.strftime("%Y-%m-%d %H:%M"),
        "seconds": round(time.time() - start), "pages_read": len(pages),
        "title": (hp.title or "").strip(), "site_name": hp.site_name,
        "headline": next((h.strip() for h in hp.h1 if h.strip()), ""),
        "description": hp.desc, "languages": langs,
        "company_linkedin": next((s for s in social if "/company/" in s), None),
        "social": social, "emails": emails, "phones": phones,
        "organization_schema": (org := org_data(pages)),
        **save_logo(base, hp, org, out),
        "page_kinds_found": sorted({p["kind"] for p in pages}),
        "thin_pages": thin,
        "note": ("Some pages show almost no text without JavaScript; read them in a browser if they matter."
                 if thin else ""),
    }
    pages_out = [{"url": p["url"], "kind": p["kind"], "title": (p["parsed"].title or "").strip(),
                  "h1": [h.strip() for h in p["parsed"].h1 if h.strip()], "description": p["parsed"].desc,
                  "text": texts[p["url"]][:6000]} for p in pages]
    (out / "pages.json").write_text(json.dumps(pages_out, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "facts.json").write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n[read] done in {facts['seconds']} s, {len(pages)} pages: {', '.join(facts['page_kinds_found'])}")
    print(f"  headline:  {facts['headline'][:90]}")
    print(f"  languages: {', '.join(langs) or '-'}")
    print(f"  LinkedIn:  {facts['company_linkedin'] or '-'}")
    print(f"  logo:      {facts['logo_file'] or '-'}")
    if facts["organization_schema"]:
        print(f"  schema:    {', '.join(facts['organization_schema'])}")
    if thin:
        print(f"  note:      {len(thin)} page(s) almost empty without JavaScript")
    print(f"\nFiles: {out}/pages.json, facts.json  (Claude reads these; nothing was judged yet)")


if __name__ == "__main__":
    main()
