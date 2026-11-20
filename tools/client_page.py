"""Build a private "صمّم غرفتي" result page for one customer.

Usage: python3 tools/client_page.py requests/<id>.json

JSON shape:
{
  "id": "k7m2q9x4",                 # random, hard to guess; becomes p/<id>.html
  "room": "صالة",                    # room type, shown in the title
  "image": "img/p/k7m2q9x4.jpg",     # the redesigned image (700x1050 or similar)
  "before": "img/p/k7m2q9x4-before.jpg",   # optional: only if the customer agreed to show it
  "items": [{"name": "كنبة ...", "asin": "B0..."}, ...]
}

The page is noindex and /p/ is disallowed in robots.txt; it is not linked from anywhere,
so only the customer with the link sees it. Amazon links live on our site (allowed),
we never put them in WhatsApp/e-mail messages: we send the page link only.
"""
import html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
TAG = "leewanhomedec-21"


def main(path):
    d = json.load(open(path, encoding="utf-8"))
    pid = d["id"]
    if not re.fullmatch(r"[a-z0-9]{6,20}", pid):
        sys.exit("id must be 6-20 lowercase letters/digits")
    tpl = open("r/dining-japandi-warm-wood.html", encoding="utf-8").read()
    style = re.search(r"<style>.*?</style>", tpl, re.S).group(0)
    nav = tpl[tpl.index("<header>"):tpl.index("<main>")].replace('href="../', 'href="../')
    footer = tpl[tpl.index("<footer>"):tpl.index("</footer>") + 9]
    room = html.escape(d.get("room", "غرفتك"))
    title = f"تصميم {room} الخاص بك | ليوان"
    items = d["items"]
    cart = "https://www.amazon.sa/gp/aws/cart/add.html?AssociateTag=" + TAG + "".join(
        f"&ASIN.{i}={it['asin']}&Quantity.{i}=1" for i, it in enumerate(items, 1))
    rows = "".join(
        f'<div class="p"><div><h3><span class="n">{i}</span> {html.escape(it["name"])}</h3>\n'
        f'<a class="btn" rel="sponsored nofollow" href="https://www.amazon.sa/dp/{it["asin"]}?tag={TAG}">شوف السعر في أمازون</a></div></div>'
        for i, it in enumerate(items, 1))
    before = ""
    if d.get("before"):
        before = (f'<p class="note">قبل:</p><img loading="lazy" src="../{html.escape(d["before"])}" '
                  f'alt="غرفتك قبل التصميم" style="max-width:100%;border-radius:12px">')
    main = (
        f'<main><div class="hero"><div><img fetchpriority="high" src="../{html.escape(d["image"])}" alt="تصميم مقترح لـ{room}">'
        '<div class="note">تصميم مقترح بالذكاء الاصطناعي. '
        'وقد تختلف تفاصيل بسيطة عن القطع الحقيقية.</div>' + before + '</div>'
        f'<div><h1>تصميم {room} الخاص بك</h1>'
        '<p>هذا التصميم جهّزناه لصورة غرفتك. اضغط على أي قطعة لتشوف سعرها الحالي في أمازون السعودية، أو أضف القطع كلها لسلتك بضغطة.</p>'
        f'<a class="btn all" rel="sponsored nofollow" href="{html.escape(cart)}">أضف كل قطع التصميم لسلة أمازون ({len(items)} قطع)</a>'
        + rows +
        '<p class="note">تبغى تعديل على التصميم؟ رد على رسالتنا ونعدّله لك. وإذا عجبك، شاركنا صورة غرفتك بعد التنفيذ 💛</p>'
        '</div></div></main>')
    out = (
        '<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{title}</title><meta name="robots" content="noindex,nofollow">'
        + style + '</head><body>\n' + nav + main + footer + '</body></html>')
    os.makedirs("p", exist_ok=True)
    open(f"p/{pid}.html", "w", encoding="utf-8").write(out)
    print(f"https://leewanhomedecor.com/p/{pid}.html?src=design_request")


if __name__ == "__main__":
    main(sys.argv[1])
