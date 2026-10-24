# -*- coding: utf-8 -*-
import subprocess
import sys
import os
import shutil

BASE_DIR = r'C:\Users\Edson\code\.vscode\量化交易\程序本体'

# 确保launcher.py存在
launcher_path = os.path.join(BASE_DIR, 'launcher.py')
if not os.path.exists(launcher_path):
    with open(launcher_path, 'w', encoding='utf-8') as f:
        f.write('''# -*- coding: utf-8 -*-
import sys
import os
sys.path.append(os.path.dirname(__file__))
from AI量化交易系统GUI import main
if __name__ == "__main__":
    main()
''')

# 使用PyInstaller打包
cmd = [
    sys.executable, '-m', 'PyInstaller',
    '--console',
    '--clean',
    '--name=AI_Trading_System',
    '--add-data=data_cache;data_cache',
    '--add-data=portfolio.pkl;.',
    'launcher.py'
]

print(f"执行命令: {' '.join(cmd)}")
result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=300)

print(f"\n返回码: {result.returncode}")
if result.returncode != 0:
    print("STDOUT:", result.stdout[-5000:] if len(result.stdout) > 5000 else result.stdout)
    print("STDERR:", result.stderr[-5000:] if len(result.stderr) > 5000 else result.stderr)
else:
    print("打包成功!")
    # 检查dist目录
    dist_dir = os.path.join(BASE_DIR, 'dist')
    if os.path.exists(dist_dir):
        for item in os.listdir(dist_dir):
            item_path = os.path.join(dist_dir, item)
            if os.path.isdir(item_path):
                print(f"\n找到目录: {item}")
                exe_path = os.path.join(item_path, 'AI_Trading_System.exe')
                if os.path.exists(exe_path):
                    print(f"  可执行文件: {exe_path}")
                    print(f"  文件大小: {os.path.getsize(exe_path) / (1024*1024):.2f} MB")