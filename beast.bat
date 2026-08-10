@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "TS_DIR=%SCRIPT_DIR%ThrottleStop"
set "TS_EXE=%TS_DIR%\ThrottleStop.exe"
set "TS_INI=%TS_DIR%\ThrottleStop.ini"
set "TS_PROFILE_INI=%SCRIPT_DIR%ThrottleStop_profiles\beast.ini"
set "LOG_FILE=%SCRIPT_DIR%switch_log.txt"

echo [%date% %time%] [beast] Starting mode switch... >> "%LOG_FILE%"

:: Step 1: Kill TS
taskkill /f /t /im ThrottleStop.exe >nul 2>&1
powershell -Command "Stop-Process -Name ThrottleStop -Force -ErrorAction SilentlyContinue" >nul 2>&1
timeout /t 1 /nobreak >nul

:: Step 2: Copy profile INI
if exist "%TS_PROFILE_INI%" (
    copy /y "%TS_PROFILE_INI%" "%TS_INI%" >nul
    echo [%date% %time%] [beast] INI copied >> "%LOG_FILE%"
) else (
    echo [beast] ERROR: beast.ini not found
    exit /b 1
)

:: Step 3: Set CPU max frequency via Windows power plan (Beast: 5.0GHz)
powercfg /setacvalueindex scheme_current sub_processor 75b0ae3f-bce0-45a7-8c89-c9611c25e100 5000
powercfg /setacvalueindex scheme_current sub_processor 75b0ae3f-bce0-45a7-8c89-c9611c25e101 5000
powercfg /setactive scheme_current
echo [beast] Power plan: Max=5.0GHz

:: Step 4: Start TS to inject FIVR
schtasks /run /tn "ThrottleStop_NoUAC" >nul 2>&1
echo [%date% %time%] [beast] TS started >> "%LOG_FILE%"

:: Step 5: Wait for FIVR injection then kill TS
timeout /t 5 /nobreak >nul
taskkill /f /t /im ThrottleStop.exe >nul 2>&1
powershell -Command "Stop-Process -Name ThrottleStop -Force -ErrorAction SilentlyContinue" >nul 2>&1
echo [%date% %time%] [beast] TS killed, done >> "%LOG_FILE%"

echo [beast] Beast Mode applied.
exit /b 0
