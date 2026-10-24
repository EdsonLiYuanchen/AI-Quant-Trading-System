# -*- coding: utf-8 -*-
"""修复AI量化交易系统GUI.py中所有剩余的emoji"""

import os

# 要查找和替换的emoji（使用Unicode转义）
emoji_map = {
    '\u2717': '[X]',  # ✗
    '\u2713': '[CHECK]',  # ✓
}

# 只处理AI量化交易系统GUI.py
filepath = "AI量化交易系统GUI.py"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换所有emoji
new_content = content
count = 0
for emoji, replacement in emoji_map.items():
    if emoji in new_content:
        count += new_content.count(emoji)
        new_content = new_content.replace(emoji, replacement)

# 保存修复后的文件
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"Fixed {count} emojis in {filepath}")
