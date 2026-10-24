# -*- coding: utf-8 -*-
"""查找并修复AI量化交易系统GUI.py中所有剩余的emoji"""

import os

# 要查找和替换的emoji
emoji_map = {
    '✅': '[OK]',
    '❌': '[ERROR]',
    '⚠️': '[WARN]',
    '📦': '[INFO]',
    '🌐': '[NET]',
    '🚀': '[RUN]',
    '💡': '[IDEA]',
    '📈': '[UP]',
    '📊': '[STAT]',
    '📋': '[LIST]',
    '🎯': '[TGT]',
    '🛡️': '[SAFE]',
    '🔍': '[FIND]',
    '💰': '[MONEY]',
    '📁': '[FILE]',
    '🔄': '[SYNC]',
    '⚡': '[FAST]',
    '📌': '[PIN]',
    '⭐': '[STAR]',
    '💹': '[CHART]',
    '🔔': '[ALERT]',
    '🎓': '[LEARN]',
    '📝': '[NOTE]',
    '🔥': '[HOT]',
    '✨': '[NEW]',
    '🧠': '[AI]',
    '📱': '[MOBILE]',
    '💻': '[PC]',
    '🌙': '[NIGHT]',
    '☀️': '[DAY]',
    '🌈': '[COLOR]',
    '🔑': '[KEY]',
    '📍': '[LOC]',
    '🕐': '[TIME]',
    '💾': '[SAVE]',
    '📤': '[OUT]',
    '📥': '[IN]',
    '🔧': '[TOOL]',
    '💼': '[WORK]',
    '🤖': '[BOT]',
    '📢': '[BROAD]',
    '🎁': '[GIFT]',
    '📚': '[BOOK]',
    '🎵': '[MUSIC]',
    '🎬': '[VIDEO]',
    '📷': '[CAM]',
    '🌊': '[WAVE]',
    '⏰': '[CLOCK]',
    '⏱️': '[TIMER]',
    '🏠': '[HOME]',
    '🏢': '[OFFICE]',
    '📞': '[PHONE]',
    '✉️': '[MAIL]',
    '🔗': '[LINK]',
    '💬': '[CHAT]',
    '👤': '[USER]',
    '👥': '[USERS]',
    '🔒': '[LOCK]',
    '🔓': '[UNLOCK]',
    '📉': '[DOWN]',
    '🔌': '[CONN]',
    '✗': '[X]',  # 注意这个小叉号
    '✓': '[CHECK]',  # 小对号
}

# 只处理AI量化交易系统GUI.py
filepath = "AI量化交易系统GUI.py"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 查找所有emoji
found_emojis = []
for emoji in emoji_map.keys():
    if emoji in content:
        found_emojis.append(emoji)

print(f"Found {len(found_emojis)} emojis in {filepath}:")
for emoji in found_emojis:
    print(f"  {emoji}")

# 替换所有emoji
new_content = content
for emoji, replacement in emoji_map.items():
    if emoji in new_content:
        new_content = new_content.replace(emoji, replacement)

# 保存修复后的文件
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"\nFixed {len(found_emojis)} emojis in {filepath}")
