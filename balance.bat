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

:: Step 3: Switch to Balanced plan and configure CPU (Balance: 4.8GHz, Efficient turbo)
powercfg /setactive 381b4222-f694-41f0-9685-ff5bb260df2e
powercfg /setacvalueindex scheme_current sub_processor be337238-0d82-4146-a960-4f3749d470c7 2
powercfg /setdcvalueindex scheme_current sub_processor be337238-0d82-4146-a960-4f3749d470c7 2
powercfg /setacvalueindex scheme_current sub_processor 75b0ae3f-bce0-45a7-8c89-c9611c25e100 4800
powercfg /setacvalueindex scheme_current sub_processor 75b0ae3f-bce0-45a7-8c89-c9611c25e101 4800
powercfg /setdcvalueindex scheme_current sub_processor 75b0ae3f-bce0-45a7-8c89-c9611c25e100 4800
powercfg /setdcvalueindex scheme_current sub_processor 75b0ae3f-bce0-45a7-8c89-c9611c25e101 4800
powercfg /setactive scheme_current
echo [balance] Balanced plan + Efficient turbo, Max=4.8GHz (AC+DC)

:: Step 4: Set GPU to Hybrid (auto-switch by system) via SYSTEM task
echo 0 > "%SCRIPT_DIR%gpu_mode.tmp"
schtasks /run /tn "LegionGpuSwitch" >nul 2>&1
echo [balance] GPU → Hybrid (Auto)

:: Step 5: Start TS, verify it launched (3s), wait for FIVR (2s)
schtasks /run /tn "ThrottleStop_NoUAC" >nul 2>&1
timeout /t 3 /nobreak >nul
tasklist /fi "imagename eq ThrottleStop.exe" 2>nul | find /i "ThrottleStop" >nul
if %errorlevel% equ 0 (
    echo [%date% %time%] [balance] TS started >> "%LOG_FILE%"
    timeout /t 2 /nobreak >nul
) else (
    echo [%date% %time%] [balance] TS FAILED to start! >> "%LOG_FILE%"
)

:: Step 6: Kill TS
taskkill /f /t /im ThrottleStop.exe >nul 2>&1
echo [%date% %time%] [balance] TS killed, done >> "%LOG_FILE%"

echo [balance] Balance Mode applied.
exit /b 0
