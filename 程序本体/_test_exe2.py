import os, subprocess, time, urllib.request
exe = os.path.join(os.getcwd(), "dist", "AI_Trading_System.exe", "AI_Trading_System.exe")
env = dict(os.environ)
env["AITRADE_NO_BROWSER"] = "1"
env["PYTHONUNBUFFERED"] = "1"
env["PYTHONIOENCODING"] = "utf-8"
p = subprocess.Popen([exe], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                     cwd=os.path.dirname(exe), env=env)
time.sleep(15)
alive = p.poll() is None
try:
    urllib.request.urlopen("http://127.0.0.1:8899/", timeout=3).read()
    print("HTTP OK")
except Exception as e:
    print("HTTP FAIL", e)
if alive:
    p.kill()
data = p.communicate()[0].decode("utf-8", "replace")
print("alive_before_kill:", alive)
print("---- stdout ----")
print(data[-3000:])
