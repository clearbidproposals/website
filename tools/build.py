#!/usr/bin/env python3
"""Build the Clearbid blog: post pages, blog index, RSS feed and sitemap.

Inputs
  tools/posts.json          list of posts: slug, title, description, date (YYYY-MM-DD),
                            optional updated (YYYY-MM-DD), service ("capability"|"review"|"proposal"|"monthly")
  tools/posts/<slug>.html   the article body (HTML fragment: lede paragraph, sections, sources list)

Outputs
  blog/<slug>/index.html, blog/index.html, blog/feed.xml, sitemap.xml

Run from the repo root:  python3 tools/build.py
"""
import datetime as dt
import html
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://www.clearbidproposals.com"
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700'
         '&family=Source+Serif+4:opsz,wght@8..60,500;8..60,650&family=IBM+Plex+Mono:wght@400;500'
         '&display=swap" rel="stylesheet">')
ICON = ("<link rel=\"icon\" href=\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
        "%3Crect width='32' height='32' rx='6' fill='%231f5c4f'/%3E%3Ctext x='16' y='22' font-family='Georgia,serif' "
        "font-size='18' font-weight='bold' fill='white' text-anchor='middle'%3EC%3C/text%3E%3C/svg%3E\">")
HEADER = '''  <header class="top">
    <a class="brand" href="/">Clear<span>bid</span> Proposal Services</a>
    <nav aria-label="Main">
      <a href="/#services">Services</a>
      <a href="/#samples">Samples</a>
      <a href="/blog/"{blog_current}>Blog</a>
      <a href="/#contact">Contact</a>
    </nav>
  </header>'''
FOOTER = '''  <footer>
    <span>© {year} Clearbid Proposal Services · Petal, Mississippi</span>
    <span><a href="/">Home</a> · <a href="/blog/">Blog</a> · <a href="/terms.html">Terms</a> · <a href="/privacy.html">Privacy</a></span>
  </footer>'''
SERVICES = {
    "capability": ("Need a capability statement?",
                   "We write one-page capability statements for small contractors, plus rewritten SBA profile text, for $300 in 3 business days.",
                   "https://buy.stripe.com/8x26oG2UCaQU0Xj7Ll7ok00", "Order a capability statement"),
    "review": ("Want a second set of eyes before you submit?",
               "Our $250 bid review checks your draft against every requirement in the solicitation and lists what is missing, in 2 business days.",
               "https://buy.stripe.com/eVq7sK66Oe36eO93v57ok01", "Order a bid review"),
    "proposal": ("Have a bid due?",
                 "Send us the solicitation and your deadline. We write complete, compliance-checked proposals at a fixed price, usually in 5 business days.",
                 "mailto:kaleb@clearbidproposals.com?subject=Proposal%20quote", "Email us the solicitation"),
    "monthly": ("Bidding every month?",
                "Monthly bid support covers up to two standard proposals a month and a weekly list of matching open bids, for $1,250 a month.",
                "https://buy.stripe.com/6oU5kC52K9MQ0Xjc1B7ok02", "Start monthly support"),
}


def esc(s):
    return html.escape(s, quote=True)


def nice_date(d):
    return d.strftime("%B %-d, %Y")


def reading_minutes(fragment):
    words = len(re.sub(r"<[^>]+>", " ", fragment).split())
    return max(1, round(words / 230))


def head(title, description, canonical, og_type, extra=""):
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{canonical}">
<link rel="alternate" type="application/rss+xml" title="Clearbid blog" href="{SITE}/blog/feed.xml">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="Clearbid Proposal Services">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:image" content="{SITE}/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
{extra}{ICON}
{FONTS}
<link rel="stylesheet" href="/assets/blog.css">
</head>
<body>
<div class="wrap">
'''


def build():
    posts = json.loads((ROOT / "tools/posts.json").read_text())
    for p in posts:
        p["d"] = dt.date.fromisoformat(p["date"])
        p["u"] = dt.date.fromisoformat(p.get("updated", p["date"]))
        p["url"] = f"{SITE}/blog/{p['slug']}/"
        p["body"] = (ROOT / "tools/posts" / f"{p['slug']}.html").read_text().strip()
        if p.get("service") and p["service"] not in SERVICES:
            sys.exit(f"unknown service for {p['slug']}: {p['service']}")
    posts.sort(key=lambda p: p["d"], reverse=True)
    slugs = [p["slug"] for p in posts]
    if len(slugs) != len(set(slugs)):
        sys.exit("duplicate slug in posts.json")
    year = dt.date.today().year

    # Post pages
    for p in posts:
        ld = {
            "@context": "https://schema.org", "@type": "BlogPosting",
            "headline": p["title"], "description": p["description"],
            "datePublished": p["d"].isoformat(), "dateModified": p["u"].isoformat(),
            "mainEntityOfPage": p["url"], "image": f"{SITE}/og-image.png",
            "author": {"@type": "Organization", "name": "Clearbid Proposal Services", "url": SITE + "/"},
            "publisher": {"@type": "Organization", "name": "Clearbid Proposal Services", "url": SITE + "/"},
        }
        extra = (f'<meta property="article:published_time" content="{p["d"].isoformat()}">\n'
                 f'<meta property="article:modified_time" content="{p["u"].isoformat()}">\n'
                 f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n')
        updated = f' · Updated {nice_date(p["u"])}' if p["u"] != p["d"] else ""
        cta = ""
        if p.get("service"):
            h, txt, href, label = SERVICES[p["service"]]
            cta = f'''
    <section class="cta">
      <h2>{esc(h)}</h2>
      <p>{esc(txt)}</p>
      <a class="btn" href="{href}">{esc(label)}</a><a class="btn ghost" href="/#services">See all services</a>
    </section>'''
        page = head(f'{p["title"]} | Clearbid', p["description"], p["url"], "article", extra)
        page += HEADER.format(blog_current="") + "\n"
        page += f'''  <p class="crumbs"><a href="/blog/">Blog</a></p>
  <article>
    <h1>{esc(p["title"])}</h1>
    <p class="meta">By Clearbid Proposal Services · <time datetime="{p["d"].isoformat()}">{nice_date(p["d"])}</time>{updated} · {reading_minutes(p["body"])} min read</p>
{p["body"]}{cta}
  </article>
''' + FOOTER.format(year=year) + "\n</div>\n</body>\n</html>\n"
        out = ROOT / "blog" / p["slug"] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page)

    # Service pages (tools/pages.json + tools/pages/<path>.html)
    pages = json.loads((ROOT / "tools/pages.json").read_text()) if (ROOT / "tools/pages.json").exists() else []
    for pg in pages:
        url = f"{SITE}/{pg['path']}/"
        ld = {"@context": "https://schema.org", "@type": "Service", "name": pg["service_name"],
              "url": url, "description": pg["description"], "areaServed": {"@type": "Country", "name": "United States"},
              "provider": {"@type": "ProfessionalService", "name": "Clearbid Proposal Services", "url": SITE + "/"},
              "offers": {"@type": "Offer", "price": pg["price"], "priceCurrency": "USD"}}
        extra = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n'
        body = (ROOT / "tools/pages" / f"{pg['path']}.html").read_text().rstrip()
        page = head(pg["title"], pg["description"], url, "website", extra)
        page += HEADER.format(blog_current="") + "\n"
        page += f'''  <p class="crumbs"><a href="/#services">Services</a></p>
  <article class="page">
{body}
  </article>
''' + FOOTER.format(year=year) + "\n</div>\n</body>\n</html>\n"
        out = ROOT / pg["path"] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page)

    # Blog index
    items = "\n".join(f'''      <li>
        <h2><a href="/blog/{p["slug"]}/">{esc(p["title"])}</a></h2>
        <p>{esc(p["description"])}</p>
        <time datetime="{p["d"].isoformat()}">{nice_date(p["d"])}</time>
      </li>''' for p in posts)
    idx = head("Blog | Clearbid Proposal Services",
               "Practical guides for small contractors on finding bids, writing proposals and capability statements, and government contracting in Mississippi.",
               f"{SITE}/blog/", "website")
    idx += HEADER.format(blog_current=' aria-current="page"') + "\n"
    idx += f'''  <section class="listing">
    <h1>Blog</h1>
    <p class="lede">Practical guides for small contractors: finding bids, writing proposals and capability statements, and getting government work in Mississippi. New articles every Wednesday.</p>
    <ul class="post-list">
{items}
    </ul>
  </section>
''' + FOOTER.format(year=year) + "\n</div>\n</body>\n</html>\n"
    (ROOT / "blog/index.html").write_text(idx)

    # RSS feed
    def rfc822(d):
        return dt.datetime(d.year, d.month, d.day, 12, 0, tzinfo=dt.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    rss_items = "\n".join(f'''  <item>
    <title>{esc(p["title"])}</title>
    <link>{p["url"]}</link>
    <guid isPermaLink="true">{p["url"]}</guid>
    <pubDate>{rfc822(p["d"])}</pubDate>
    <description>{esc(p["description"])}</description>
  </item>''' for p in posts)
    last = rfc822(posts[0]["d"]) if posts else rfc822(dt.date.today())
    (ROOT / "blog/feed.xml").write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>Clearbid Proposal Services blog</title>
  <link>{SITE}/blog/</link>
  <atom:link href="{SITE}/blog/feed.xml" rel="self" type="application/rss+xml"/>
  <description>Practical guides for small contractors on bids, proposals and government contracting.</description>
  <language>en-us</language>
  <lastBuildDate>{last}</lastBuildDate>
{rss_items}
</channel>
</rss>
''')

    # Sitemap
    newest = posts[0]["u"].isoformat() if posts else dt.date.today().isoformat()
    static = [("/", None)] + [(f"/{pg['path']}/", None) for pg in pages] + [("/blog/", newest), ("/terms.html", None), ("/privacy.html", None)]
    urls = []
    for path, lastmod in static:
        if lastmod is None:
            f = "index.html" if path == "/" else path.lstrip("/")
            if f.endswith("/"):
                f = "tools/pages/" + f.rstrip("/") + ".html"
            r = subprocess.run(["git", "log", "-1", "--format=%cs", "--", f], cwd=ROOT, capture_output=True, text=True)
            lastmod = r.stdout.strip() or dt.date.today().isoformat()
        urls.append(f"  <url><loc>{SITE}{path}</loc><lastmod>{lastmod}</lastmod></url>")
    for p in posts:
        urls.append(f"  <url><loc>{p['url']}</loc><lastmod>{p['u'].isoformat()}</lastmod></url>")
    (ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                                      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                      + "\n".join(urls) + "\n</urlset>\n")
    print(f"built {len(posts)} post(s): " + ", ".join(slugs) + f"; {len(pages)} page(s)")


if __name__ == "__main__":
    build()
