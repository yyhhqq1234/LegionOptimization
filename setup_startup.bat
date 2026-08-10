@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ============================================================
:: LegionOptimization — One-time Startup Setup
:: Run once as administrator
:: ============================================================

set "SCRIPT_DIR=%~dp0"
set "LLT_EXE=C:\Program Files\LenovoLegionToolkit\Lenovo Legion Toolkit.exe"
set "TS_DIR=%SCRIPT_DIR%ThrottleStop"

:: Check admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] This script requires Administrator privileges.
    echo Right-click setup_startup.bat ^> Run as administrator
    pause
    exit /b 1
)

echo ============================================================
echo   LegionOptimization — Startup Setup
echo ============================================================
echo.
echo This will create 4 scheduled tasks:
echo   1. LegionLLT             — LLT to system tray at logon
echo   2. LegionProfile         — FIVR injector on boot (+30s)
echo   3. ThrottleStop_NoUAC    — TS launcher without UAC
echo   4. LegionUpdate          — Weekly LLT update check (Sun 3:00 AM)
echo.
echo After reboot:
echo   Logon ^> LLT starts ^> detects power mode
echo   ^> runs automation ^> batch script ^>
echo     kill TS ^> copy INI ^> powercfg ^> TS inject ^> kill TS
echo ============================================================
echo.

:: Verify files
if not exist "%LLT_EXE%" (
    echo [ERROR] LLT not found at: %LLT_EXE%
    echo Install from: https://github.com/LenovoLegionToolkit-Team/LenovoLegionToolkit/releases
    pause
    exit /b 1
)
if not exist "%TS_DIR%\ThrottleStop.exe" (
    echo [ERROR] ThrottleStop not found at: %TS_DIR%
    pause
    exit /b 1
)
if not exist "%SCRIPT_DIR%\start_llt.ps1" (
    echo [ERROR] start_llt.ps1 not found
    pause
    exit /b 1
)
if not exist "%SCRIPT_DIR%\startup.ps1" (
    echo [ERROR] startup.ps1 not found
    pause
    exit /b 1
)
if not exist "%SCRIPT_DIR%\PowerModeWatcher.ps1" (
    echo [ERROR] PowerModeWatcher.ps1 not found
    pause
    exit /b 1
)
if not exist "%SCRIPT_DIR%\check_update.ps1" (
    echo [ERROR] check_update.ps1 not found
    pause
    exit /b 1
)

echo Files verified OK.
echo.

:: ============================================================
:: Task 1: LLT Auto-Start
:: ============================================================
echo [1/4] Creating LegionLLT...
schtasks /delete /tn "LegionLLT" /f >nul 2>&1
schtasks /create /tn "LegionLLT" ^
    /tr "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \"%SCRIPT_DIR%start_llt.ps1\"" ^
    /sc ONLOGON ^
    /rl HIGHEST ^
    /f
if %errorlevel% equ 0 (
    echo   LegionLLT [OK]
) else (
    echo   LegionLLT [FAILED] — errorlevel=%errorlevel%
)

:: ============================================================
:: Task 2: Startup FIVR Injector
:: ============================================================
echo [2/4] Creating LegionProfile...
schtasks /delete /tn "LegionProfile" /f >nul 2>&1
schtasks /create /tn "LegionProfile" ^
    /tr "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \"%SCRIPT_DIR%startup.ps1\"" ^
    /sc ONLOGON ^
    /delay 0000:30 ^
    /rl HIGHEST ^
    /f
if %errorlevel% equ 0 (
    echo   LegionProfile [OK]
) else (
    echo   LegionProfile [FAILED] — errorlevel=%errorlevel%
)

:: ============================================================
:: Task 3: ThrottleStop NoUAC Launcher
:: ============================================================
echo [3/4] Creating ThrottleStop_NoUAC...
schtasks /delete /tn "ThrottleStop_NoUAC" /f >nul 2>&1
schtasks /create /tn "ThrottleStop_NoUAC" ^
    /tr "\"%TS_DIR%\ThrottleStop.exe\"" ^
    /sc ONCE /st "00:00" ^
    /rl HIGHEST ^
    /f
if %errorlevel% equ 0 (
    echo   ThrottleStop_NoUAC [OK]
) else (
    echo   ThrottleStop_NoUAC [FAILED] — errorlevel=%errorlevel%
)

:: ============================================================
:: Task 4: Weekly LLT Auto-Update Check
:: ============================================================
echo [4/4] Creating LegionUpdate...
schtasks /delete /tn "LegionUpdate" /f >nul 2>&1
schtasks /create /tn "LegionUpdate" ^
    /tr "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \"%SCRIPT_DIR%check_update.ps1\"" ^
    /sc WEEKLY /d SUN /st 03:00 ^
    /rl HIGHEST ^
    /f
if %errorlevel% equ 0 (
    echo   LegionUpdate [OK]
) else (
    echo   LegionUpdate [FAILED] — errorlevel=%errorlevel%
)

:: ============================================================
:: Verify all tasks
:: ============================================================
echo.
echo === Verification ===
echo.
schtasks /query /tn "LegionLLT" /fo TABLE /nh
schtasks /query /tn "LegionProfile" /fo TABLE /nh
schtasks /query /tn "ThrottleStop_NoUAC" /fo TABLE /nh
schtasks /query /tn "LegionUpdate" /fo TABLE /nh

echo.
echo ============================================================
echo   Setup complete. Reboot to test.
echo ============================================================
pause
exit /b 0
