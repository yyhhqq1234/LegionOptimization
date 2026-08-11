@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "TS_DIR=%SCRIPT_DIR%ThrottleStop"
set "TS_EXE=%TS_DIR%\ThrottleStop.exe"
set "TS_INI=%TS_DIR%\ThrottleStop.ini"
set "TS_PROFILE_INI=%SCRIPT_DIR%ThrottleStop_profiles\quiet.ini"
set "LOG_FILE=%SCRIPT_DIR%switch_log.txt"

echo [%date% %time%] [quiet] Starting mode switch... >> "%LOG_FILE%"

:: Step 1: Kill TS
taskkill /f /t /im ThrottleStop.exe >nul 2>&1
powershell -Command "Stop-Process -Name ThrottleStop -Force -ErrorAction SilentlyContinue" >nul 2>&1
timeout /t 1 /nobreak >nul

:: Step 2: Copy profile INI
if exist "%TS_PROFILE_INI%" (
    copy /y "%TS_PROFILE_INI%" "%TS_INI%" >nul
    echo [%date% %time%] [quiet] INI copied >> "%LOG_FILE%"
) else (
    echo [quiet] ERROR: quiet.ini not found
    exit /b 1
)

:: Step 3: Balanced plan + Efficient Turbo (Quiet: 3.8GHz, smooth & battery-friendly)
powercfg /setactive 381b4222-f694-41f0-9685-ff5bb260df2e
powercfg /setacvalueindex scheme_current sub_processor be337238-0d82-4146-a960-4f3749d470c7 2
powercfg /setdcvalueindex scheme_current sub_processor be337238-0d82-4146-a960-4f3749d470c7 2
powercfg /setacvalueindex scheme_current sub_processor 75b0ae3f-bce0-45a7-8c89-c9611c25e100 3800
powercfg /setacvalueindex scheme_current sub_processor 75b0ae3f-bce0-45a7-8c89-c9611c25e101 3800
powercfg /setdcvalueindex scheme_current sub_processor 75b0ae3f-bce0-45a7-8c89-c9611c25e100 3800
powercfg /setdcvalueindex scheme_current sub_processor 75b0ae3f-bce0-45a7-8c89-c9611c25e101 3800
powercfg /setactive scheme_current
echo [quiet] Balanced + Efficient Turbo, Max=3.8GHz (AC+DC)

:: Step 4: Set GPU to iGPU Only (energy saving) via SYSTEM task
echo 2 > "%SCRIPT_DIR%gpu_mode.tmp"
schtasks /run /tn "LegionGpuSwitch" >nul 2>&1
echo [quiet] GPU → iGPU Only

:: Step 5: Start TS, verify it launched (3s), wait for FIVR (2s)
schtasks /run /tn "ThrottleStop_NoUAC" >nul 2>&1
timeout /t 3 /nobreak >nul
tasklist /fi "imagename eq ThrottleStop.exe" 2>nul | find /i "ThrottleStop" >nul
if %errorlevel% equ 0 (
    echo [%date% %time%] [quiet] TS started >> "%LOG_FILE%"
    timeout /t 2 /nobreak >nul
) else (
    echo [%date% %time%] [quiet] TS FAILED to start! >> "%LOG_FILE%"
)

:: Step 6: Kill TS
taskkill /f /t /im ThrottleStop.exe >nul 2>&1
echo [%date% %time%] [quiet] TS killed, done >> "%LOG_FILE%"

echo [quiet] Quiet Mode applied.
exit /b 0
