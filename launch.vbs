' VibeGrade Launcher
' Starts the Flask server silently and opens the browser

Dim WshShell
Set WshShell = CreateObject("WScript.Shell")

' Change directory to the project folder
WshShell.CurrentDirectory = "C:\Users\MT\Projects\colorgrading"

' Kill any existing instance on port 5000 (silent, using PowerShell for safety/accuracy)
WshShell.Run "powershell -WindowStyle Hidden -Command ""Stop-Process -Id (Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue).OwningProcess -Force -ErrorAction SilentlyContinue""", 0, True

' Start the Flask server hidden via run.bat
WshShell.Run """C:\Users\MT\Projects\colorgrading\run.bat""", 0, False

' Wait for the server to boot (2.5 seconds)
WScript.Sleep 2500

' Open the browser to VibeGrade
WshShell.Run "http://localhost:5000"

Set WshShell = Nothing
