import io, re
p = "web/app.js"
src = io.open(p, encoding="utf-8").read()

pat = re.compile(r"\$\((\s*'#[A-Za-z0-9_\-]+'\s*)\)\.addEventListener\(")
print("binding matches:", len(pat.findall(src)))

# boot() 范围起点
b = src.index("function boot() {")
e = src.index("document.addEventListener('DOMContentLoaded'")
boot = src[b:e]
print("bindings inside boot():", len(pat.findall(boot)))
print("bindings outside boot():", len(pat.findall(src)) - len(pat.findall(boot)))
