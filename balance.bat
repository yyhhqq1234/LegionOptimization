@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "TS_DIR=%SCRIPT_DIR%ThrottleStop"
set "TS_EXE=%TS_DIR%\ThrottleStop.exe"
set "TS_INI=%TS_DIR%\ThrottleStop.ini"
set "TS_PROFILE_INI=%SCRIPT_DIR%ThrottleStop_profiles\balance.ini"
set "LOG_FILE=%SCRIPT_DIR%switch_log.txt"

echo [%date% %time%] [balance] Starting mode switch... >> "%LOG_FILE%"

:: Step 1: Kill TS
taskkill /f /t /im ThrottleStop.exe >nul 2>&1
powershell -Command "Stop-Process -Name ThrottleStop -Force -ErrorAction SilentlyContinue" >nul 2>&1
timeout /t 1 /nobreak >nul

:: Step 2: Copy profile INI
if exist "%TS_PROFILE_INI%" (
    copy /y "%TS_PROFILE_INI%" "%TS_INI%" >nul
    echo [%date% %time%] [balance] INI copied >> "%LOG_FILE%"
) else (
    echo [balance] ERROR: balance.ini not found
    exit /b 1
)

:: Step 3: Set CPU max frequency via Windows power plan (Balance: 4.8GHz)
powercfg /setacvalueindex scheme_current sub_processor 75b0ae3f-bce0-45a7-8c89-c9611c25e100 4800
powercfg /setacvalueindex scheme_current sub_processor 75b0ae3f-bce0-45a7-8c89-c9611c25e101 4800
powercfg /setactive scheme_current
echo [balance] Power plan: Max=4.8GHz

:: Step 4: Start TS to inject FIVR
schtasks /run /tn "ThrottleStop_NoUAC" >nul 2>&1
echo [%date% %time%] [balance] TS started >> "%LOG_FILE%"

:: Step 5: Wait for FIVR injection then kill TS
timeout /t 5 /nobreak >nul
taskkill /f /t /im ThrottleStop.exe >nul 2>&1
powershell -Command "Stop-Process -Name ThrottleStop -Force -ErrorAction SilentlyContinue" >nul 2>&1
echo [%date% %time%] [balance] TS killed, done >> "%LOG_FILE%"

echo [balance] Balance Mode applied.
exit /b 0
