# -*- coding: utf-8 -*-
"""修复持仓管理.py中的emoji"""

import os

filepath = os.path.join(os.path.dirname(__file__), "持仓管理.py")

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换所有emoji
content = content.replace('[OK]', '[OK]')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed 持仓管理.py")
