import os, subprocess, time, urllib.request, sys
exe = os.path.join(os.getcwd(), "dist", "AI_Trading_System.exe", "AI_Trading_System.exe")
env = dict(os.environ)
env["AITRADE_NO_BROWSER"] = "1"
env["PYTHONIOENCODING"] = "utf-8"
out = open("test10_out.txt", "wb")
p = subprocess.Popen([exe], stdout=out, stderr=subprocess.STDOUT, cwd=os.path.dirname(exe), env=env)
ok = False
for i in range(40):
    time.sleep(1)
    if p.poll() is not None:
        print("EXITED early, code", p.returncode)
        break
    try:
        r = urllib.request.urlopen("http://127.0.0.1:8899/", timeout=3)
        body = r.read()
        print("HTTP", r.status, "bytes", len(body))
        ok = True
        break
    except Exception:
        pass
if p.poll() is None:
    p.kill()
out.close()
print("RESULT:", "OK" if ok else "FAIL")
print("---- output ----")
print(open("test10_out.txt", encoding="utf-8", errors="replace").read()[-2500:])
