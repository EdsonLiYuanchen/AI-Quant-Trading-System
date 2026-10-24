import zipfile, os, shutil
base = os.getcwd()
tmp = os.path.join(base, "_verify_extract")
if os.path.isdir(tmp):
    shutil.rmtree(tmp)
os.makedirs(tmp)
with zipfile.ZipFile(os.path.join("dist", "AI量化交易系统_便携版.zip")) as z:
    z.extractall(tmp)
root = os.path.join(tmp, "AI量化交易系统_便携版", "app")
print("app dir:", os.path.isdir(root))
print("exe:", os.path.isfile(os.path.join(root, "AI_Trading_System.exe")))
print("app.js size:", os.path.getsize(os.path.join(root, "_internal", "web", "app.js")))
