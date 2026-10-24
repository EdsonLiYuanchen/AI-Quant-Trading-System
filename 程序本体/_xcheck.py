import re, io
js = io.open("web/app.js", encoding="utf-8").read()
html = io.open("web/index.html", encoding="utf-8").read()

html_ids = set(re.findall(r'id="([^"]+)"', html))
js_ids = set(re.findall(r"""\$\(\s*['"]#([A-Za-z0-9_\-]+)['"]\s*\)""", js))
missing = sorted(i for i in js_ids if i not in html_ids)
print("ids referenced in js:", len(js_ids))
print("missing in html (%d):" % len(missing))
for m in missing:
    print("   #" + m)

# nav-btn / page pairs
navs = set(re.findall(r'data-page="([^"]+)"', html))
print("\nnav pages in html:", sorted(navs))
missing_pages = [n for n in navs if ('page-' + n) not in html_ids]
print("nav pages with no #page-* container:", missing_pages)
