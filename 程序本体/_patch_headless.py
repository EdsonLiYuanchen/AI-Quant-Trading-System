import io
p = r"headless_server.py"
src = io.open(p, encoding="utf-8").read()
anchor = "if __name__ == '__main__':"
new_block = '''def serve_local(host='127.0.0.1', port=8899, open_browser=True):
    """本地一次性服务模式：无 pywebview 时的回退方案。
    启动本地 HTTP 服务器，自动打开默认浏览器显示界面，并保持进程前台运行。"""
    import webbrowser
    api, server = _make_server(host, port, None)
    print('=' * 60)
    print('AI 量化交易系统 · 本地界面模式已启动')
    print('  访问地址: http://127.0.0.1:%d' % port)
    print('  停止方式: 关闭本窗口，或按 Ctrl+C')
    print('=' * 60)
    if open_browser:
        try:
            webbrowser.open('http://127.0.0.1:%d' % port)
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\\n服务已停止')
        server.shutdown()


'''
assert anchor in src
src = src.replace(anchor, new_block + anchor, 1)
io.open(p, "w", encoding="utf-8").write(src)
print("OK")
