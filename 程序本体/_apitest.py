import os, subprocess, time, json, urllib.request
appdir = os.path.join(os.getcwd(), "dist", "AI量化交易系统_便携版", "app")
exe = os.path.join(appdir, "AI_Trading_System.exe")
print("exists:", os.path.isfile(exe), "internal:", os.path.isdir(os.path.join(appdir, "_internal")))
env = dict(os.environ); env["AITRADE_NO_BROWSER"] = "1"
p = subprocess.Popen([exe], cwd=appdir, env=env,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
port = None
for i in range(60):
    time.sleep(1)
    for pt in range(8899, 8912):
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/" % pt, timeout=2).read()
            port = pt; break
        except Exception:
            pass
    if port or p.poll() is not None:
        break
print("server port:", port, "exe alive:", p.poll() is None)

def post(name, args=None):
    body = json.dumps({"args": args or []}).encode()
    req = urllib.request.Request("http://127.0.0.1:%d/api/%s" % (port, name), data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=60)
        return r.status, r.read().decode("utf-8", "replace")[:150]
    except Exception as e:
        return "ERR", "%s: %s" % (type(e).__name__, str(e)[:130])

if port:
    for name in ["ping", "ui_init", "watch_list", "portfolio_get", "trading_status",
                 "db_status", "storage_get", "backtest_models", "rt_overview",
                 "fund_records_get", "trading_get_config", "ai_strategy_config_get"]:
        print(name, "->", post(name))
if p.poll() is None:
    p.kill()
