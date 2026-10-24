# -*- coding: utf-8 -*-
import os

dist_dir = r'C:\Users\Edson\code\.vscode\量化交易\程序本体\dist'

if os.path.exists(dist_dir):
    print(f"dist目录存在: {dist_dir}")
    contents = os.listdir(dist_dir)
    print(f"目录内容: {contents}")
    
    for item in contents:
        item_path = os.path.join(dist_dir, item)
        if os.path.isdir(item_path):
            print(f"\n子目录 {item}:")
            sub_contents = os.listdir(item_path)
            exe_files = [f for f in sub_contents if f.endswith('.exe')]
            if exe_files:
                print(f"  可执行文件: {exe_files}")
                for exe in exe_files:
                    exe_path = os.path.join(item_path, exe)
                    print(f"  文件大小: {os.path.getsize(exe_path) / (1024*1024):.2f} MB")
            else:
                print(f"  没有找到可执行文件")
else:
    print(f"dist目录不存在: {dist_dir}")