' Stop VibeGrade
' Silently stops the Flask server running on port 5000

Dim WshShell
Set WshShell = CreateObject("WScript.Shell")

' Kill the process on port 5000 using PowerShell
WshShell.Run "powershell -WindowStyle Hidden -Command ""Stop-Process -Id (Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue).OwningProcess -Force -ErrorAction SilentlyContinue""", 0, True

Set WshShell = Nothing
