# -*- coding: utf-8 -*-
import os

dist_dir = r'C:\Users\Edson\code\.vscode\量化交易\程序本体\dist'

print(f"检查目录: {dist_dir}")

if os.path.exists(dist_dir):
    items = os.listdir(dist_dir)
    print(f"\n目录内容 ({len(items)} 个项目):")
    for item in items:
        item_path = os.path.join(dist_dir, item)
        if os.path.isdir(item_path):
            print(f"  [目录] {item}")
            # 检查是否有akshare目录
            akshare_path = os.path.join(item_path, 'akshare')
            if os.path.exists(akshare_path):
                print(f"    - 包含akshare目录")
                file_fold_path = os.path.join(akshare_path, 'file_fold')
                if os.path.exists(file_fold_path):
                    print(f"    - 包含file_fold目录")
                    files = os.listdir(file_fold_path)[:5]
                    print(f"    - file_fold内容: {files}...")
        else:
            size = os.path.getsize(item_path) / (1024 * 1024)
            print(f"  [文件] {item} ({size:.2f} MB)")