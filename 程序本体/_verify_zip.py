import os, zipfile, subprocess, time, urllib.request, shutil, tempfile
base = os.getcwd()
zip_path = os.path.join(base, "dist", "AI量化交易系统_便携版.zip")
tmp = os.path.join(tempfile.gettempdir(), "aitrade_verify")
if os.path.isdir(tmp):
    shutil.rmtree(tmp)
os.makedirs(tmp)
with zipfile.ZipFile(zip_path) as zf:
    zf.extractall(tmp)
root = os.path.join(tmp, "AI量化交易系统_便携版")
print("extracted:", os.listdir(root)[:10])
exe = os.path.join(root, "app", "AI_Trading_System.exe")
print("exe exists:", os.path.isfile(exe), "bat:", os.path.isfile(os.path.join(root, "启动.bat")))
env = dict(os.environ); env["AITRADE_NO_BROWSER"] = "1"
p = subprocess.Popen([exe], cwd=os.path.dirname(exe), env=env,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
ok = False
for i in range(60):
    time.sleep(1)
    if p.poll() is not None:
        print("EXITED code", p.returncode); break
    try:
        r = urllib.request.urlopen("http://127.0.0.1:8899/", timeout=3)
        b = r.read()
        html = b.decode("utf-8", "replace")
        print("HTTP", r.status, "bytes", len(b))
        ok = True
        print("title tag:", html[html.find("<title"):html.find("</title>")+8])
        break
    except Exception:
        pass
if p.poll() is None:
    p.kill()
print("VERIFY:", "PASS" if ok else "FAIL")
shutil.rmtree(tmp, ignore_errors=True)
