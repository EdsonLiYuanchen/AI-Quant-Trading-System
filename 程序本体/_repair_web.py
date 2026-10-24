import io
p = r"AI量化交易系统Web.py"
raw = open(p, "rb").read()
text = raw.decode("utf-8", errors="replace")
lines = text.splitlines()
out = []
i = 0
fixed = False
while i < len(lines):
    ln = lines[i]
    if (not fixed) and ln.strip().startswith("import webview"):
        out.append("    import webview  # noqa: E402  # 桌面版需要；无头模式不依赖")
        fixed = True
        i += 1
        # drop following continuation junk lines that are not valid python
        while i < len(lines) and lines[i].lstrip().startswith("）"):
            i += 1
        continue
    out.append(ln)
    i += 1
assert fixed, "import webview line not found"
open(p, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("repaired")
