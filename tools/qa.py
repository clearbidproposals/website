#!/usr/bin/env python3
"""Pre-publish checks for the Clearbid site. Run from the repo root: python3 tools/qa.py
Fails (exit 1) on: broken internal links/anchors, unparseable XML or JSON-LD, leftover placeholders,
a post without sources, or a post fragment missing from the build."""
import html.parser, json, pathlib, re, sys, xml.dom.minidom
ROOT = pathlib.Path(__file__).resolve().parent.parent
errors = []
pages = [p for p in ROOT.rglob("*.html") if "tools" not in p.parts and ".git" not in p.parts]

class P(html.parser.HTMLParser):
    def __init__(s): super().__init__(); s.links=[]; s.ids=set(); s.ld=[]; s._ld=False; s.text=[]
    def handle_starttag(s, t, a):
        a = dict(a)
        if "id" in a: s.ids.add(a["id"])
        if t == "a" and a.get("href"): s.links.append(a["href"])
        if t in ("link", "script", "img") and (a.get("href") or a.get("src")) and a.get("rel") != "preconnect":
            v = a.get("href") or a.get("src")
            if not v.startswith("data:"): s.links.append(v)
        s._ld = (t == "script" and a.get("type") == "application/ld+json")
    def handle_data(s, d):
        if s._ld: s.ld.append(d)
        else: s.text.append(d)
    def handle_endtag(s, t): s._ld = False

parsed = {}
for p in pages:
    x = P(); x.feed(p.read_text()); parsed[p] = x
    for blob in x.ld:
        try: json.loads(blob)
        except Exception as e: errors.append(f"{p.relative_to(ROOT)}: bad JSON-LD ({e})")
    txt = " ".join(x.text)
    for bad in ["TODO", "TBD", "lorem", "[INSERT", "{{", "PO Box 60"]:
        if bad in txt: errors.append(f"{p.relative_to(ROOT)}: contains '{bad}'")

def resolve(page, href):
    href = href.split("?")[0]
    path, _, frag = href.partition("#")
    if path == "": target = page
    elif path.startswith("/"): target = ROOT / path.lstrip("/")
    else: target = (page.parent / path).resolve()
    if target.is_dir() or path.endswith("/"): target = target / "index.html"
    return target, frag

for p, x in parsed.items():
    for href in x.links:
        if re.match(r"^(https?:|mailto:|tel:)", href): continue
        target, frag = resolve(p, href)
        if not target.exists(): errors.append(f"{p.relative_to(ROOT)}: broken link {href}"); continue
        if frag and target in parsed and frag not in parsed[target].ids:
            errors.append(f"{p.relative_to(ROOT)}: missing anchor {href}")

for f in ["sitemap.xml", "blog/feed.xml"]:
    try: xml.dom.minidom.parse(str(ROOT / f))
    except Exception as e: errors.append(f"{f}: invalid XML ({e})")

posts = json.loads((ROOT / "tools/posts.json").read_text())
for post in posts:
    out = ROOT / "blog" / post["slug"] / "index.html"
    if not out.exists(): errors.append(f"post not built: {post['slug']}")
    body = (ROOT / "tools/posts" / f"{post['slug']}.html").read_text()
    if "<h2>Sources</h2>" not in body or body.count("<li><a href=\"http") < 2:
        errors.append(f"post without a sources list: {post['slug']}")
    if len(post["description"]) > 170: errors.append(f"description too long ({len(post['description'])}): {post['slug']}")
    if len(post["title"]) > 70: errors.append(f"title too long ({len(post['title'])}): {post['slug']}")
    words = len(re.sub(r"<[^>]+>", " ", body).split())
    print(f"{post['slug']}: {words} words")

print("\n".join(errors) if errors else f"OK: {len(pages)} pages checked")
sys.exit(1 if errors else 0)
