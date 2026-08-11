@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "TS_DIR=%SCRIPT_DIR%ThrottleStop"
set "TS_EXE=%TS_DIR%\ThrottleStop.exe"
set "TS_INI=%TS_DIR%\ThrottleStop.ini"
set "TS_PROFILE_INI=%SCRIPT_DIR%ThrottleStop_profiles\custom.ini"
set "LOG_FILE=%SCRIPT_DIR%switch_log.txt"

echo [%date% %time%] [custom] Starting mode switch... >> "%LOG_FILE%"

:: Step 1: Kill TS
taskkill /f /t /im ThrottleStop.exe >nul 2>&1
powershell -Command "Stop-Process -Name ThrottleStop -Force -ErrorAction SilentlyContinue" >nul 2>&1
timeout /t 1 /nobreak >nul

:: Step 2: Copy profile INI
if exist "%TS_PROFILE_INI%" (
    copy /y "%TS_PROFILE_INI%" "%TS_INI%" >nul
    echo [%date% %time%] [custom] INI copied >> "%LOG_FILE%"
) else (
    echo [custom] ERROR: custom.ini not found
    exit /b 1
)

:: Step 3: Switch to Ultimate/High Performance plan and configure CPU (Extreme: 5.2GHz, Aggressive turbo)
powercfg /setactive e9a42b02-d5df-448d-aa00-03f14749eb61 2>nul || powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
powercfg /setacvalueindex scheme_current sub_processor be337238-0d82-4146-a960-4f3749d470c7 1
powercfg /setdcvalueindex scheme_current sub_processor be337238-0d82-4146-a960-4f3749d470c7 1
powercfg /setacvalueindex scheme_current sub_processor 75b0ae3f-bce0-45a7-8c89-c9611c25e100 5200
powercfg /setacvalueindex scheme_current sub_processor 75b0ae3f-bce0-45a7-8c89-c9611c25e101 5200
powercfg /setdcvalueindex scheme_current sub_processor 75b0ae3f-bce0-45a7-8c89-c9611c25e100 5200
powercfg /setdcvalueindex scheme_current sub_processor 75b0ae3f-bce0-45a7-8c89-c9611c25e101 5200
powercfg /setactive scheme_current
echo [custom] Ultimate Perf plan + Aggressive turbo, Max=5.2GHz (AC+DC)

:: Step 4: Start TS, verify it launched (3s), wait for FIVR (2s)
schtasks /run /tn "ThrottleStop_NoUAC" >nul 2>&1
timeout /t 3 /nobreak >nul
tasklist /fi "imagename eq ThrottleStop.exe" 2>nul | find /i "ThrottleStop" >nul
if %errorlevel% equ 0 (
    echo [%date% %time%] [custom] TS started >> "%LOG_FILE%"
    timeout /t 2 /nobreak >nul
) else (
    echo [%date% %time%] [custom] TS FAILED to start! >> "%LOG_FILE%"
)

:: Step 5: Kill TS
taskkill /f /t /im ThrottleStop.exe >nul 2>&1
echo [%date% %time%] [custom] TS killed, done >> "%LOG_FILE%"

echo [custom] Custom Mode applied.
exit /b 0
