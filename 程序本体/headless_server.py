# -*- coding: utf-8 -*-
"""
AI 量化交易系统 · 无头 HTTP 服务（24h 自动交易模式）
=====================================================
在任意电脑/云服务器上运行 `python main_web.py --server`，
即可用浏览器/手机访问控制面板，引擎在服务进程内常驻，
服务器重启后按 engine_state.json 自动续跑，直到点击「停止」。

用法:
    python main_web.py --server                 # 0.0.0.0:8000 无令牌
    python main_web.py --server --port 8000 --host 0.0.0.0
    python main_web.py --server --token 你的密码   # 访问需带令牌
"""
import os
import sys
import json
import subprocess
import urllib.parse
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from AI量化交易系统Web import WebApi, resource_path, _to_jsonable  # noqa: E402

MIME = {
    '.html': 'text/html; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
}


def _fmt_exc(e):
    return '%s: %s' % (type(e).__name__, e)


class ApiHandler(BaseHTTPRequestHandler):
    api = None          # WebApi 实例（类属性，进程级单例）
    web_root = None     # 静态资源根目录
    token = None        # 访问令牌，None 表示不校验

    # ---------------- 工具 ----------------
    def log_message(self, fmt, *args):
        pass  # 关闭默认访问日志，避免刷屏

    def _send(self, code, body, ctype='application/json; charset=utf-8'):
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Api-Token')
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False))

    def _check_token(self):
        if not self.token:
            return True
        header = self.headers.get('X-Api-Token', '')
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        qtoken = (qs.get('token') or [''])[0]
        return (header == self.token) or (qtoken == self.token)

    # ---------------- 路由 ----------------
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Api-Token')
        self.end_headers()

    def do_GET(self):
        if not self._check_token():
            self._send_json({'ok': False, 'msg': '访问令牌错误'}, 403)
            return
        path = urllib.parse.urlparse(self.path).path
        if path.startswith('/api/'):
            method = path[len('/api/'):]
            fn = getattr(self.api, method, None)
            if fn is None:
                self._send_json({'ok': False, 'msg': '接口不存在: %s' % method}, 404)
                return
            try:
                result = fn()
                self._send_json(_to_jsonable(result))
            except Exception as e:
                self._send_json({'ok': False, 'msg': '接口异常: %s' % _fmt_exc(e)}, 500)
            return
        # 静态资源
        if path in ('', '/'):
            path = '/index.html'
        rel = path.lstrip('/')
        if rel in ('', 'index.html', 'app.js', 'style.css') or rel.startswith(('assets/', 'static/')):
            pass
        file_path = os.path.join(self.web_root, rel)
        if not os.path.isfile(file_path) or '..' in rel:
            self._send(404, b'<h1>404 Not Found</h1>', 'text/html; charset=utf-8')
            return
        ext = os.path.splitext(file_path)[1].lower()
        with open(file_path, 'rb') as f:
            self._send(200, f.read(), MIME.get(ext, 'application/octet-stream'))

    def do_POST(self):
        if not self._check_token():
            self._send_json({'ok': False, 'msg': '访问令牌错误'}, 403)
            return
        path = urllib.parse.urlparse(self.path).path
        if not path.startswith('/api/'):
            self._send_json({'ok': False, 'msg': '接口不存在'}, 404)
            return
        method = path[len('/api/'):]
        fn = getattr(self.api, method, None)
        if fn is None:
            self._send_json({'ok': False, 'msg': '接口不存在: %s' % method}, 404)
            return
        args, kwargs = [], {}
        try:
            length = int(self.headers.get('Content-Length') or 0)
            if length > 0:
                raw = self.rfile.read(length).decode('utf-8')
                if raw.strip():
                    payload = json.loads(raw)
                    if isinstance(payload, dict):
                        args = payload.get('args', []) or []
                        kwargs = payload.get('kwargs', {}) or {}
                    elif isinstance(payload, list):
                        args = payload
        except Exception:
            pass
        try:
            result = fn(*args, **kwargs)
            self._send_json(_to_jsonable(result))
        except TypeError as e:
            self._send_json({'ok': False, 'msg': '参数错误: %s' % _fmt_exc(e)}, 400)
        except Exception as e:
            self._send_json({'ok': False, 'msg': '接口异常: %s' % _fmt_exc(e)}, 500)


def _make_server(host, port, token):
    api = WebApi()
    try:
        r = api.trading.auto_resume()
        if r.get('ok'):
            print('[AUTO] 已自动续跑上次未停止的交易引擎')
        else:
            print('[AUTO] 引擎未在运行，等待手动启动')
    except Exception as e:
        print('[AUTO] 自动续跑检查失败: %s' % _fmt_exc(e))
    ApiHandler.api = api
    ApiHandler.web_root = resource_path('web')
    ApiHandler.token = token
    server = ThreadingHTTPServer((host, port), ApiHandler)
    server.daemon_threads = True
    return api, server


def start_server(host='0.0.0.0', port=8000, token=None):
    """非阻塞启动：在后台线程 serving。供 Android 前台服务等调用。"""
    api, server = _make_server(host, port, token)
    print('[SERVER] listening on %s:%d' % (host, port))
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return {'ok': True, 'msg': 'listening %s:%d' % (host, port)}


def run_server(host='0.0.0.0', port=8000, token=None):
    api, server = _make_server(host, port, token)
    print('=' * 60)
    print('AI 量化交易系统 · 24h 自动交易服务已启动')
    print('  本地访问 : http://127.0.0.1:%d' % port)
    print('  局域网访问: http://<本机IP>:%d' % port)
    print('  令牌     : %s' % (token or '未启用（仅建议内网使用）'))
    print('  停止方式 : 在网页中点「停止」→ 引擎退出；关服务进程则引擎停止')
    print('  提示     : 进程存活期间引擎持续交易；机器重启后服务会自动续跑')
    print('=' * 60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n服务已停止')
        server.shutdown()


def _find_browsers():
    """按优先级返回可用于「应用窗口」模式的浏览器可执行文件。"""
    import shutil
    found = []
    for name in ('msedge', 'chrome'):
        p = shutil.which(name)
        if p:
            found.append(p)
    for p in (
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    ):
        if os.path.isfile(p) and p not in found:
            found.append(p)
    return found


def serve_local(host='127.0.0.1', port=8899, open_browser=True):
    """本地一次性服务模式：无 pywebview 时的回退方案。
    启动本地 HTTP 服务器，并用 Edge/Chrome 的「应用窗口」模式打开界面，
    外观与桌面软件一致（无地址栏）；找不到浏览器时退回默认浏览器。"""
    import webbrowser

    api, server = None, None
    for p in range(port, port + 12):
        try:
            api, server = _make_server(host, p, None)
            port = p
            break
        except OSError:
            continue
    if server is None:
        print('[错误] 无法监听本地端口，请关闭占用端口的程序后重试')
        return

    url = 'http://127.0.0.1:%d' % port
    print('=' * 60)
    print('AI 量化交易系统 · 本地界面模式已启动')
    print('  访问地址: %s' % url)
    print('  停止方式: 关闭本窗口，或按 Ctrl+C')
    print('=' * 60)

    launched = False
    if open_browser and not os.environ.get('AITRADE_NO_BROWSER'):
        for exe in _find_browsers():
            try:
                subprocess.Popen([exe, '--app=%s' % url,
                                  '--window-size=1360,900', '--no-first-run'])
                launched = True
                break
            except Exception:
                continue
        if not launched:
            try:
                webbrowser.open(url)
                launched = True
            except Exception:
                pass
    if not launched:
        print('请手动在浏览器中打开上面的访问地址')

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n服务已停止')
        server.shutdown()


if __name__ == '__main__':
    host = '0.0.0.0'
    port = 8000
    token = os.environ.get('AITRADE_TOKEN')
    argv = sys.argv[1:]
    for i, a in enumerate(argv):
        if a in ('--host',) and i + 1 < len(argv):
            host = argv[i + 1]
        elif a in ('--port',) and i + 1 < len(argv):
            port = int(argv[i + 1])
        elif a in ('--token',) and i + 1 < len(argv):
            token = argv[i + 1]
    run_server(host=host, port=port, token=token)
