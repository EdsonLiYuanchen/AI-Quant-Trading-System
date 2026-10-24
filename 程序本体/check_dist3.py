# -*- coding: utf-8 -*-
import os

dist_dir = r'C:\Users\Edson\code\.vscode\量化交易\程序本体\dist'

print(f"检查目录: {dist_dir}")
print(f"目录存在: {os.path.exists(dist_dir)}")

if os.path.exists(dist_dir):
    items = os.listdir(dist_dir)
    print(f"\n目录内容 ({len(items)} 个项目):")
    for item in items:
        item_path = os.path.join(dist_dir, item)
        if os.path.isdir(item_path):
            print(f"  [目录] {item}")
            sub_items = os.listdir(item_path)[:5]
            if sub_items:
                print(f"    子项目: {sub_items}...")
        else:
            size = os.path.getsize(item_path) / (1024 * 1024)
            print(f"  [文件] {item} ({size:.2f} MB)")