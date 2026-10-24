@echo off
chcp 65001 >nul
title 修复emoji字符

echo 正在修复emoji字符问题...

:: 进入程序目录
cd /d "%~dp0"

:: 批量替换emoji字符（使用sed或其他方法）
powershell -Command "Get-ChildItem -Filter '*.py' | ForEach-Object { (Get-Content $_.FullName -Raw) -replace '✅', '[OK]' -replace '⚠️', '[WARN]' -replace '📦', '[INFO]' -replace '❌', '[ERROR]' -replace '🌐', '[NET]' -replace '🚀', '[RUN]' -replace '💡', '[IDEA]' -replace '📈', '[UP]' -replace '📊', '[STAT]' -replace '📋', '[LIST]' -replace '🎯', '[TGT]' -replace '🛡️', '[SAFE]' -replace '🔍', '[FIND]' -replace '💰', '[MONEY]' -replace '📁', '[FILE]' -replace '🔄', '[SYNC]' -replace '⚡', '[FAST]' -replace '📌', '[PIN]' -replace '⭐', '[STAR]' -replace '💹', '[CHART]' -replace '🔔', '[ALERT]' -replace '🎓', '[LEARN]' -replace '📝', '[NOTE]' -replace '🔥', '[HOT]' -replace '✨', '[NEW]' -replace '🧠', '[AI]' -replace '📱', '[MOBILE]' -replace '💻', '[PC]' -replace '🌙', '[NIGHT]' -replace '☀️', '[DAY]' -replace '🌈', '[COLOR]' -replace '🔑', '[KEY]' -replace '📍', '[LOC]' -replace '🕐', '[TIME]' -replace '💾', '[SAVE]' -replace '📤', '[OUT]' -replace '📥', '[IN]' -replace '🔧', '[TOOL]' -replace '💼', '[WORK]' -replace '🤖', '[BOT]' -replace '📢', '[BROAD]' -replace '🎁', '[GIFT]' -replace '📚', '[BOOK]' -replace '🎵', '[MUSIC]' -replace '🎬', '[VIDEO]' -replace '📷', '[CAM]' -replace '💡', '[LIGHT]' -replace '🌊', '[WAVE]' -replace '⏰', '[CLOCK]' -replace '⏱️', '[TIMER]' -replace '📌', '[PIN]' -replace '🏠', '[HOME]' -replace '🏢', '[OFFICE]' -replace '📞', '[PHONE]' -replace '✉️', '[MAIL]' -replace '🔗', '[LINK]' -replace '💬', '[CHAT]' -replace '👤', '[USER]' -replace '👥', '[USERS]' -replace '🔒', '[LOCK]' -replace '🔓', '[UNLOCK]' -replace '📊', '[CHART]' -replace '📉', '[DOWN]' -replace '📈', '[UP]' | Set-Content $_.FullName -NoNewline }"

echo 完成！
pause
