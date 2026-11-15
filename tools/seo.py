#!/usr/bin/env python3
"""Leewan SEO pass. Idempotent: safe to run after every site regeneration.

Adds canonical/Open Graph/Twitter/JSON-LD tags, better meta descriptions,
one <h1> per page, image dimensions, related-design links, sitemap.xml
(with image entries) and robots.txt.

Usage: python3 tools/seo.py   (run from the repo root)
"""
import datetime, html, json, os, re, glob

SITE = "https://leewanhomedecor.com"
NAME = "ليوان"
FULL_NAME = "ليوان | ديكور وتنسيق منزلي"
IMG_W, IMG_H = 700, 1050
TODAY = datetime.date.today().isoformat()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

STATIC_DESC = {
    "about.html": "تعرّف على ليوان: مشروع سعودي يجمع أفكار ديكور كاملة لكل غرف البيت، بقطع حقيقية متوفرة في أمازون السعودية.",
    "contact.html": "تواصل مع فريق ليوان لأي استفسار عن تصاميم الديكور أو القطع المقترحة.",
    "privacy.html": "سياسة الخصوصية لموقع ليوان: كيف نتعامل مع بياناتك وروابط شركاء أمازون.",
}
HOME_DESC = ("أفكار ديكور كاملة لكل غرف البيت: مجالس، صالات، غرف نوم، مطابخ، حمامات وغرف أطفال. "
             "شوف التصميم واطلب كل قطعة فيه من أمازون السعودية.")

SEO_START, SEO_END = "<!--seo-->", "<!--/seo-->"
REL_START, REL_END = "<!--related-->", "<!--/related-->"


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def write(p, s):
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


def is_redirect(s):
    return 'http-equiv="refresh"' in s


def text(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def page_title(s):
    m = re.search(r"<title>(.*?)</title>", s, re.S)
    return text(m.group(1)) if m else NAME


def clip(s, n=158):
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) <= n:
        return s
    cut = s[:n].rsplit(" ", 1)[0].rstrip("،,.:؛-–")
    return cut + "…"


def url_for(path):
    return SITE + "/" if path == "index.html" else f"{SITE}/{path}"


# ---------- collect design + category data ----------
designs = {}  # slug path -> {title, img, items}
for p in sorted(glob.glob("r/*.html")):
    s = read(p)
    if is_redirect(s):
        continue
    m = re.search(r"<h[12]>(.*?)</h[12]>", s[s.find("<main>"):], re.S)
    title = text(m.group(1)) if m else page_title(s).split("|")[0].strip()
    img = re.search(r'<div class="hero"><div><img[^>]*src="\.\./(img/[^"]+)"', s)
    items = [re.sub(r"^\d+\s*", "", text(h)) for h in re.findall(r"<h3>(.*?)</h3>", s, re.S)]
    designs[p] = {"title": title, "img": img.group(1) if img else None, "items": items}

categories = {}  # c/x.html -> {name, members:[r/..]}
for p in sorted(glob.glob("c/*.html")):
    s = read(p)
    m = re.search(r"<main><h[12]>(.*?)</h[12]>", s, re.S)
    name = text(m.group(1)) if m else page_title(s).split("|")[0].strip()
    members = ["r/" + x for x in re.findall(r'href="\.\./r/([^"]+)"', s)]
    categories[p] = {"name": name, "members": [x for x in members if x in designs]}

design_cat = {}
for c, d in categories.items():
    for r in d["members"]:
        design_cat.setdefault(r, c)


# ---------- head tags ----------
def head_block(path, title, desc, image, kind, jsonld):
    u = url_for(path)
    img_url = f"{SITE}/{image}" if image else None
    tags = [
        f'<link rel="canonical" href="{u}">',
        f'<meta property="og:site_name" content="{FULL_NAME}">',
        '<meta property="og:locale" content="ar_SA">',
        f'<meta property="og:type" content="{kind}">',
        f'<meta property="og:title" content="{html.escape(title)}">',
        f'<meta property="og:description" content="{html.escape(desc)}">',
        f'<meta property="og:url" content="{u}">',
        '<meta name="robots" content="index,follow,max-image-preview:large">',
        '<meta name="theme-color" content="#3b2a1a">',
    ]
    if img_url:
        tags += [
            f'<meta property="og:image" content="{img_url}">',
            f'<meta property="og:image:width" content="{IMG_W}">',
            f'<meta property="og:image:height" content="{IMG_H}">',
            '<meta name="twitter:card" content="summary_large_image">',
            f'<meta name="twitter:image" content="{img_url}">',
        ]
    else:
        tags.append('<meta name="twitter:card" content="summary">')
    tags += [
        f'<meta name="twitter:title" content="{html.escape(title)}">',
        f'<meta name="twitter:description" content="{html.escape(desc)}">',
    ]
    for obj in jsonld:
        tags.append('<script type="application/ld+json">' +
                    json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "</script>")
    return SEO_START + "".join(tags) + SEO_END


def breadcrumbs(chain):
    return {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": url_for(p)}
            for i, (n, p) in enumerate(chain)
        ],
    }


def set_head(s, block, desc):
    s = re.sub(re.escape(SEO_START) + ".*?" + re.escape(SEO_END), "", s, flags=re.S)
    # drop any stray canonical left by the generator so there is exactly one
    s = re.sub(r'<link rel="canonical"[^>]*>', "", s)
    if re.search(r'<meta name="description"[^>]*>', s):
        s = re.sub(r'<meta name="description"[^>]*>',
                   f'<meta name="description" content="{html.escape(desc)}">', s, count=1)
    else:
        s = s.replace("</title>", f'</title><meta name="description" content="{html.escape(desc)}">', 1)
    return s.replace("</head>", block + "</head>", 1)


def demote_logo(s):
    """Site name in header becomes a styled div so each page has one real <h1>."""
    s = s.replace("<h1>ليوان | ديكور وتنسيق منزلي</h1>",
                  '<div class="logo">ليوان | ديكور وتنسيق منزلي</div>')
    if ".logo{" not in s:
        s = s.replace("</style>",
                      "header .logo{margin:0;font-size:26px;font-weight:700}"
                      "main h1{font-size:1.5em;margin:.83em 0}</style>", 1)
    return s


def promote_main_heading(s):
    i = s.find("<main>")
    if i < 0 or re.search(r"<h1>", s[i:]):
        return s
    tail = re.sub(r"<h2>(.*?)</h2>", r"<h1>\1</h1>", s[i:], count=1, flags=re.S)
    return s[:i] + tail


def size_images(s, lazy_from=0):
    """Add width/height (stops layout shift); keep the first images eager for LCP."""
    n = [0]

    def fix(m):
        tag = m.group(0)
        if "/img/" not in tag and 'src="img/' not in tag:
            return tag
        k = n[0]; n[0] += 1
        if "width=" not in tag:
            tag = tag.replace("<img ", f'<img width="{IMG_W}" height="{IMG_H}" ', 1)
        if k < lazy_from:
            tag = tag.replace(' loading="lazy"', "")
            if "fetchpriority" not in tag and k == 0:
                tag = tag.replace("<img ", '<img fetchpriority="high" ', 1)
        elif "loading=" not in tag:
            tag = tag.replace("<img ", '<img loading="lazy" ', 1)
        return tag

    s = re.sub(r"<img [^>]*>", fix, s)
    if "img{max-width:100%;height:auto}" not in s:
        s = s.replace("<style>", "<style>img{max-width:100%;height:auto}", 1)
    return s


def related_block(path):
    c = design_cat.get(path)
    if not c:
        return ""
    others = [r for r in categories[c]["members"] if r != path]
    if not others:
        return ""
    # rotate so each page links to different neighbours
    k = categories[c]["members"].index(path)
    picks = (others[k:] + others[:k])[:4]
    cards = "".join(
        f'<a class="card" href="../{r}"><img loading="lazy" width="{IMG_W}" height="{IMG_H}" '
        f'src="../{designs[r]["img"]}" alt="{html.escape(designs[r]["title"])}">'
        f'<div>{html.escape(designs[r]["title"])}</div></a>'
        for r in picks if designs[r]["img"])
    name = categories[c]["name"]
    return (f'{REL_START}<section class="related"><h2>تصاميم مشابهة</h2>'
            f'<div class="grid">{cards}</div>'
            f'<p><a href="../{c}">كل أفكار {html.escape(name)} ←</a></p></section>{REL_END}')


def set_related(s, block):
    s = re.sub(re.escape(REL_START) + ".*?" + re.escape(REL_END), "", s, flags=re.S)
    if block:
        s = s.replace("</main>", block + "</main>", 1)
        s = s.replace(".related{margin-top:28px}.related h2{font-size:20px}", "")
        if ".related .grid{" not in s:
            s = s.replace("</style>", ".related{margin-top:28px}.related h2{font-size:20px}"
                          ".related .grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}"
                          "@media(min-width:720px){.related .grid{grid-template-columns:repeat(4,minmax(0,1fr))}}"
                          ".related .card div{font-size:13px}</style>", 1)
    return s


# ---------- per-page processing ----------
pages = []  # (path, image list) for sitemap

for path in ["index.html", *sorted(STATIC_DESC)]:
    if not os.path.exists(path):
        continue
    s = read(path)
    title = page_title(s)
    if path == "index.html":
        desc = HOME_DESC
        jsonld = [
            {"@context": "https://schema.org", "@type": "WebSite", "name": FULL_NAME,
             "alternateName": "Leewan Home Decor", "url": SITE + "/", "inLanguage": "ar"},
            {"@context": "https://schema.org", "@type": "Organization", "name": "Leewan Home Decor",
             "url": SITE + "/",
             "sameAs": ["https://www.tiktok.com/@leewan.home.decor",
                        "https://www.pinterest.com/leewanhomedecor/"]},
        ]
        first = re.search(r'src="(img/[^"]+)"', s)
        image = first.group(1) if first else None
        s = set_head(s, head_block(path, title, desc, image, "website", jsonld), desc)
        s = size_images(s, lazy_from=2)
        imgs = re.findall(r'src="(img/[^"]+)"', s)
    else:
        desc = STATIC_DESC[path]
        s = set_head(s, head_block(path, title, desc, None, "website",
                                   [breadcrumbs([(NAME, "index.html"), (title.split("|")[0].strip(), path)])]), desc)
        s = demote_logo(s)
        s = promote_main_heading(s)
        imgs = []
    write(path, s)
    pages.append((path, imgs))

for path, c in categories.items():
    s = read(path)
    title = page_title(s)
    titles = [designs[r]["title"].replace(" كامل من أمازون", "").replace(" كاملة من أمازون", "")
              for r in c["members"][:3]]
    n = len(c["members"])
    word = "أفكار" if 3 <= n <= 10 else "فكرة"
    desc = clip(f"{n} {word} {c['name']} كاملة بقطع حقيقية من أمازون السعودية، منها: "
                + "، ".join(titles) + ".")
    title = f"أفكار ديكور {c['name']} كاملة | {NAME}"
    s = re.sub(r"<title>.*?</title>", f"<title>{html.escape(title)}</title>", s, count=1, flags=re.S)
    image = designs[c["members"][0]]["img"] if c["members"] else None
    jsonld = [
        breadcrumbs([(NAME, "index.html"), (c["name"], path)]),
        {"@context": "https://schema.org", "@type": "CollectionPage", "name": title,
         "url": url_for(path), "inLanguage": "ar",
         "mainEntity": {"@type": "ItemList", "itemListElement": [
             {"@type": "ListItem", "position": i + 1, "url": url_for(r), "name": designs[r]["title"]}
             for i, r in enumerate(c["members"])]}},
    ]
    s = set_head(s, head_block(path, title, desc, image, "website", jsonld), desc)
    s = demote_logo(s)
    s = promote_main_heading(s)
    s = size_images(s, lazy_from=2)
    write(path, s)
    pages.append((path, [designs[r]["img"] for r in c["members"] if designs[r]["img"]]))

for path, d in designs.items():
    s = read(path)
    title = page_title(s)
    base = d["title"]
    short = re.sub(r"\s+كامل[ة]? من أمازون$", "", base)
    items = "، ".join(d["items"][:3])
    desc = clip(f"{short}: {len(d['items'])} قطع منسّقة منها {items}. "
                "شوف التصميم واطلب كل قطعة من أمازون السعودية.", 160) if d["items"] else base
    c = design_cat.get(path)
    chain = [(NAME, "index.html")] + ([(categories[c]["name"], c)] if c else []) + [(base, path)]
    jsonld = [breadcrumbs(chain)]
    if d["img"]:
        jsonld.append({"@context": "https://schema.org", "@type": "ImageObject",
                       "contentUrl": f"{SITE}/{d['img']}", "name": base, "description": desc,
                       "width": IMG_W, "height": IMG_H, "inLanguage": "ar"})
    s = set_head(s, head_block(path, title, desc, d["img"], "article", jsonld), desc)
    s = demote_logo(s)
    s = promote_main_heading(s)
    s = size_images(s, lazy_from=1)
    s = set_related(s, related_block(path))
    write(path, s)
    pages.append((path, [d["img"]] if d["img"] else []))

# ---------- sitemap + robots ----------
prio = {"index.html": "1.0"}
out = ['<?xml version="1.0" encoding="UTF-8"?>',
       '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
       'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">']
for path, imgs in pages:
    p = prio.get(path, "0.8" if path.startswith("c/") else "0.7" if path.startswith("r/") else "0.3")
    out.append(f"<url><loc>{url_for(path)}</loc><lastmod>{TODAY}</lastmod><priority>{p}</priority>")
    for im in dict.fromkeys(imgs):
        out.append(f"<image:image><image:loc>{SITE}/{im}</image:loc></image:image>")
    out.append("</url>")
out.append("</urlset>")
write("sitemap.xml", "\n".join(out) + "\n")
write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n")

print(f"SEO pass done: {len(pages)} pages, {len(designs)} designs, {len(categories)} categories")
