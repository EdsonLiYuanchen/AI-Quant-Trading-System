@echo off
chcp 936 >nul
set "shortcut=%USERPROFILE%\Desktop\AI_Trading_System.lnk"
set "target=C:\Users\Edson\code\.vscode\量化交易\程序本体\启动量化交易系统.bat"
set "workdir=C:\Users\Edson\code\.vscode\量化交易\程序本体"

powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%shortcut%'); $s.TargetPath = '%target%'; $s.WorkingDirectory = '%workdir%'; $s.Description = 'AI Trading System'; $s.Save()"

echo Shortcut created successfully!
pause
