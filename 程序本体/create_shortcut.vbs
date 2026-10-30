Set WshShell = CreateObject("WScript.Shell")
Set Shortcut = WshShell.CreateShortcut(WshShell.SpecialFolders("Desktop") & "\AI_Trading_System.lnk")
Shortcut.TargetPath = "C:\Users\Edson\code\.vscode\量化交易\程序本体\start_trading.bat"
Shortcut.WorkingDirectory = "C:\Users\Edson\code\.vscode\量化交易\程序本体"
Shortcut.Description = "AI Trading System"
Shortcut.Save