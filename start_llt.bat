@echo off
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%llt-build"

:: Launch LLT
start "" /min dotnet "Lenovo Legion Toolkit.dll"

:: Launch WMI watcher for 超能 mode (file-locked, only one instance runs)
timeout /t 3 /nobreak >nul
start "" /min powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%SCRIPT_DIR%PowerModeWatcher.ps1"
