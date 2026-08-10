# start_llt.ps1 — Silent LLT + Watcher launcher
# Called by LegionLLT scheduled task at logon
$scriptDir = $PSScriptRoot

# Launch LLT silently (Windows GUI app, goes to system tray)
Start-Process -FilePath "C:\Program Files\LenovoLegionToolkit\Lenovo Legion Toolkit.exe" -WindowStyle Hidden

# Wait for LLT to initialize
Start-Sleep -Seconds 5

# Launch WMI watcher for 超能 mode (file-locked, only one instance runs)
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptDir\PowerModeWatcher.ps1`"" -WindowStyle Hidden
