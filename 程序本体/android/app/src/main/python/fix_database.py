# -*- coding: utf-8 -*-
"""只修复database_manager.py中的emoji"""

import os

# 只修复database_manager.py
filepath = os.path.join(os.path.dirname(__file__), "database_manager.py")

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换所有emoji
content = content.replace('[OK]', '[OK]')
content = content.replace('[ERROR]', '[ERROR]')
content = content.replace('[WARN]', '[WARN]')
content = content.replace('[CONN]', '[CONN]')
content = content.replace('[STAT]', '[STAT]')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed database_manager.py")
