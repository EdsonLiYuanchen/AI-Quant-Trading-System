import io, re
p = "web/app.js"
src = io.open(p, encoding="utf-8").read()
orig = src

# 1) 修复失效的按钮绑定：原来绑到已删除的 #btnImportPos，
#    导致 boot() 抛错、其后所有交互全部失效。
old = """  // 导入自选按钮已移除
  $('#btnImportPos').addEventListener('click', importPosToPool);
  // 导入推荐按钮已移除
"""
new = """  on('#btnImportWatch', 'click', importWatchToPool);
  on('#btnImportAlloc', 'click', importAllocToPool);
  on('#btnImportPos', 'click', importPosToPool);
"""
assert old in src, "stale binding block not found"
src = src.replace(old, new, 1)

# 2) 所有按钮绑定改为 null 安全，避免个别元素缺失时整页交互失效
pat = re.compile(r"\$\((\s*'#[A-Za-z0-9_\-]+'\s*)\)\.addEventListener\(")
src, n = pat.subn(lambda m: "on(%s, " % m.group(1), src)
print("rewritten bindings:", n)

# 3) 插入 on() 辅助函数
anchor = "function $(sel) { return document.querySelector(sel); }"
assert anchor in src
helper = anchor + """
// 安全绑定：元素不存在时静默跳过，避免单个按钮缺失导致整页交互失效
function on(sel, ev, fn) {
  const el = $(sel);
  if (el) el.addEventListener(ev, fn);
  return el;
}"""
src = src.replace(anchor, helper, 1)

io.open(p, "w", encoding="utf-8", newline="\n").write(src)
print("changed:", orig != src)
