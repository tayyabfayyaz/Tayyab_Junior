' ─────────────────────────────────────────────────────────────────────────────
' FTE — Silent Windows Launcher (Startup Folder fallback)
' Launches WSL bash start-watchers.sh silently with no console window.
'
' Install: Copy this file to your Windows Startup folder
'   Press Win+R → type: shell:startup → paste this file there
' ─────────────────────────────────────────────────────────────────────────────

Dim oShell
Set oShell = CreateObject("WScript.Shell")

' Wait 30 seconds for WSL to initialise after login
WScript.Sleep 30000

' Run WSL command silently (0 = hidden window, False = don't wait)
oShell.Run "wsl.exe bash /mnt/d/hackathon-FTE/scripts/start-watchers.sh", 0, False

Set oShell = Nothing
