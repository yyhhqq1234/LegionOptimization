@echo off
set "SCRIPT_DIR=%~dp0"

:: Launch official LLT (Windows GUI app, no console popup)
start "" "C:\Program Files\LenovoLegionToolkit\Lenovo Legion Toolkit.exe"

:: Launch WMI watcher for 超能 mode (file-locked, only one instance runs)
timeout /t 3 /nobreak >nul
start "" /min powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%SCRIPT_DIR%PowerModeWatcher.ps1"
