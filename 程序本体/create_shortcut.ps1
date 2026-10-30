# Create desktop shortcut for trading system

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\AI_Trading_System.lnk")
$Shortcut.TargetPath = "C:\Users\Edson\code\.vscode\量化交易\程序本体\启动量化交易系统.bat"
$Shortcut.WorkingDirectory = "C:\Users\Edson\code\.vscode\量化交易\程序本体"
$Shortcut.Description = "AI Trading System"
$Shortcut.Save()

Write-Host "Shortcut created: AI_Trading_System.lnk" -ForegroundColor Green