import io
p = r"AI量化交易系统Web.py"
lines = io.open(p, encoding="utf-8").readlines()
lines.insert(19, "from AI量化交易系统GUI import EasyTraderAPI  # noqa: E402  供 headless/local 模式下单用\n")
io.open(p, "w", encoding="utf-8").writelines(lines)
print("inserted")
# verify
src = io.open(p, encoding="utf-8").read()
assert "from AI量化交易系统GUI import EasyTraderAPI" in src
print("verified")
