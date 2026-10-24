# -*- coding: utf-8 -*-
"""检查是否还有遗漏的emoji"""

import os

# 要查找的emoji
target_emoji = '🔄'  # \U0001f504

# 获取当前目录
script_dir = os.path.dirname(os.path.abspath(__file__))

# 遍历所有.py文件
for filename in os.listdir(script_dir):
    if filename.endswith('.py'):
        filepath = os.path.join(script_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                if target_emoji in content:
                    print(f"Found emoji in: {filename}")
        except Exception as e:
            print(f"Error reading {filename}: {e}")

print("Done!")
