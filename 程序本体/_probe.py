import io
p = r"AI量化交易系统Web.py"
lines = io.open(p, encoding="utf-8").readlines()
# find the comment line after "import pandas as pd"
for i, l in enumerate(lines):
    if l.strip().startswith("import pandas"):
        print("found at", i, l)
        break
# show around
for j in range(i, i+3):
    print(j, repr(lines[j]))
