import io
lines = io.open(r"AI量化交易系统Web.py", encoding="utf-8", errors="replace").read().splitlines()
for i in range(26, 34):
    print(i+1, ascii(lines[i]))
