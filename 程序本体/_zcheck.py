import zipfile, os
z = zipfile.ZipFile(os.path.join("dist", "AI量化交易系统_便携版.zip"))
names = z.namelist()
print("entries:", len(names))
for key in ["启动.bat", "使用说明.txt", "app/AI_Trading_System.exe",
            "app/_internal/web/index.html", "app/_internal/web/app.js", "app/_internal/web/style.css",
            "app/_internal/akshare/file_fold/calendar.json"]:
    hit = [n for n in names if n.endswith(key)]
    print(("OK  " if hit else "MISS"), key)
print("--- 启动.bat ---")
print(z.read([n for n in names if n.endswith("启动.bat")][0]).decode("utf-8"))
