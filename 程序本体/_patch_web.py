import io
p = r"AI量化交易系统Web.py"
src = io.open(p, encoding="utf-8").read()
# remove the 3 stray lines that got appended at the very end
stray = "    # 桌面窗口模式不可用（如 pywebview 在冻结环境缺失）时，自动改为"
lines = src.splitlines()
while lines and lines[-1].strip() == stray.strip():
    lines.pop()
src = "\n".join(lines) + "\n"
old = """    api = WebApi()
    if not HAS_WEBVIEW:
        print('未安装 pywebview，桌面窗口模式不可用；请使用 --server 无头服务模式。')
        return
    html_path = os.path.abspath(resource_path(os.path.join('web', 'index.html')))
    window = webview.create_window(
        'AI 量化交易系统',
        url=html_path,
        js_api=api,
        width=1280,
        height=820,
        min_size=(1080, 700),
        background_color='#0f1420',
    )
    webview.start(debug=False)"""
new = """    api = WebApi()
    if not HAS_WEBVIEW:
        # 冻结环境下 pywebview 缺失时，自动改用本地 HTTP 服务器 + 默认浏览器
        import webbrowser
        from headless_server import serve_local
        print('pywebview 不可用，改用本地浏览器模式...')
        serve_local(host='127.0.0.1', port=8899, open_browser=True)
        return
    html_path = os.path.abspath(resource_path(os.path.join('web', 'index.html')))
    window = webview.create_window(
        'AI 量化交易系统',
        url=html_path,
        js_api=api,
        width=1280,
        height=820,
        min_size=(1080, 700),
        background_color='#0f1420',
    )
    webview.start(debug=False)"""
assert old in src, "pattern not found"
src = src.replace(old, new)
io.open(p, "w", encoding="utf-8").write(src)
print("OK")
