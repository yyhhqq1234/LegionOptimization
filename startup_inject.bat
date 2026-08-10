@echo off
:: Startup: ensure ThrottleStop is running (once, for hotkey switching)
tasklist /fi "IMAGENAME eq ThrottleStop.exe" 2>nul | find /i "ThrottleStop.exe" >nul
if %errorlevel% neq 0 (
    schtasks /run /tn "ThrottleStop_NoUAC" >nul 2>&1
)
exit /b 0
