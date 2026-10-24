# -*- coding: utf-8 -*-
import os

dist_dir = r'C:\Users\Edson\code\.vscode\量化交易\程序本体\dist'

for item in os.listdir(dist_dir):
    item_path = os.path.join(dist_dir, item)
    print(f"文件/目录: {item}")
    if os.path.isdir(item_path):
        print(f"  是目录，包含: {os.listdir(item_path)[:10]}...")
    else:
        print(f"  是文件，大小: {os.path.getsize(item_path) / (1024*1024):.2f} MB")