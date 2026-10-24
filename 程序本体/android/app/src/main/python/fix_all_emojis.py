# -*- coding: utf-8 -*-
"""全面修复所有Python文件中的emoji字符"""

import os

# 要修复的emoji列表
emoji_map = {
    '[OK]': '[OK]',
    '[ERROR]': '[ERROR]',
    '[WARN]': '[WARN]',
    '[INFO]': '[INFO]',
    '[NET]': '[NET]',
    '[RUN]': '[RUN]',
    '[IDEA]': '[IDEA]',
    '[UP]': '[UP]',
    '[STAT]': '[STAT]',
    '[LIST]': '[LIST]',
    '[TGT]': '[TGT]',
    '[SAFE]': '[SAFE]',
    '[FIND]': '[FIND]',
    '[MONEY]': '[MONEY]',
    '[FILE]': '[FILE]',
    '[SYNC]': '[SYNC]',
    '[FAST]': '[FAST]',
    '[PIN]': '[PIN]',
    '[STAR]': '[STAR]',
    '[CHART]': '[CHART]',
    '[ALERT]': '[ALERT]',
    '[LEARN]': '[LEARN]',
    '[NOTE]': '[NOTE]',
    '[HOT]': '[HOT]',
    '[NEW]': '[NEW]',
    '[AI]': '[AI]',
    '[MOBILE]': '[MOBILE]',
    '[PC]': '[PC]',
    '[NIGHT]': '[NIGHT]',
    '[DAY]': '[DAY]',
    '[COLOR]': '[COLOR]',
    '[KEY]': '[KEY]',
    '[LOC]': '[LOC]',
    '[TIME]': '[TIME]',
    '[SAVE]': '[SAVE]',
    '[OUT]': '[OUT]',
    '[IN]': '[IN]',
    '[TOOL]': '[TOOL]',
    '[WORK]': '[WORK]',
    '[BOT]': '[BOT]',
    '[BROAD]': '[BROAD]',
    '[GIFT]': '[GIFT]',
    '[BOOK]': '[BOOK]',
    '[MUSIC]': '[MUSIC]',
    '[VIDEO]': '[VIDEO]',
    '[CAM]': '[CAM]',
    '[WAVE]': '[WAVE]',
    '[CLOCK]': '[CLOCK]',
    '[TIMER]': '[TIMER]',
    '[HOME]': '[HOME]',
    '[OFFICE]': '[OFFICE]',
    '[PHONE]': '[PHONE]',
    '[MAIL]': '[MAIL]',
    '[LINK]': '[LINK]',
    '[CHAT]': '[CHAT]',
    '[USER]': '[USER]',
    '[USERS]': '[USERS]',
    '[LOCK]': '[LOCK]',
    '[UNLOCK]': '[UNLOCK]',
    '[DOWN]': '[DOWN]',
    '[CONN]': '[CONN]',
}

def fix_emojis_in_file(filepath):
    """修复单个文件中的emoji字符"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        has_changes = False
        new_content = content
        for emoji, replacement in emoji_map.items():
            if emoji in new_content:
                new_content = new_content.replace(emoji, replacement)
                has_changes = True
        
        if has_changes:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

# 获取当前目录
script_dir = os.path.dirname(os.path.abspath(__file__))

# 处理所有.py文件
py_files = [f for f in os.listdir(script_dir) if f.endswith('.py')]
count = 0

for filename in py_files:
    filepath = os.path.join(script_dir, filename)
    if fix_emojis_in_file(filepath):
        print(f"Fixed: {filename}")
        count += 1

print(f"\nDone! Fixed {count} files.")
