@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ============================================================
:: LegionOptimization — One-time Startup Setup
:: Run once as administrator
:: ============================================================

set "SCRIPT_DIR=%~dp0"
set "LLT_DIR=%SCRIPT_DIR%llt-build"
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
echo This will create 3 scheduled tasks:
echo   1. LegionLLT             — LLT to system tray at logon
echo   2. LegionProfile         — FIVR injector on boot (+30s)
echo   3. ThrottleStop_NoUAC    — TS launcher without UAC
echo.
echo After reboot:
echo   Logon ^> LLT starts ^> detects power mode
echo   ^> runs automation ^> batch script ^>
echo     kill TS ^> copy INI ^> powercfg ^> TS inject ^> kill TS
echo ============================================================
echo.

:: Verify files
if not exist "%LLT_DIR%\Lenovo Legion Toolkit.dll" (
    echo [ERROR] LLT not found at: %LLT_DIR%
    pause
    exit /b 1
)
if not exist "%TS_DIR%\ThrottleStop.exe" (
    echo [ERROR] ThrottleStop not found at: %TS_DIR%
    pause
    exit /b 1
)
if not exist "%SCRIPT_DIR%\start_llt.bat" (
    echo [ERROR] start_llt.bat not found
    pause
    exit /b 1
)
if not exist "%SCRIPT_DIR%\startup_inject.bat" (
    echo [ERROR] startup_inject.bat not found
    pause
    exit /b 1
)

echo Files verified OK.
echo.

:: ============================================================
:: Task 1: LLT Auto-Start
:: ============================================================
echo [1/3] Creating LegionLLT...
schtasks /delete /tn "LegionLLT" /f >nul 2>&1
schtasks /create /tn "LegionLLT" ^
    /tr "\"%SCRIPT_DIR%\start_llt.bat\"" ^
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
echo [2/3] Creating LegionProfile...
schtasks /delete /tn "LegionProfile" /f >nul 2>&1
schtasks /create /tn "LegionProfile" ^
    /tr "\"%SCRIPT_DIR%\startup_inject.bat\"" ^
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
echo [3/3] Creating ThrottleStop_NoUAC...
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
:: Verify all tasks
:: ============================================================
echo.
echo === Verification ===
echo.
schtasks /query /tn "LegionLLT" /fo TABLE /nh
schtasks /query /tn "LegionProfile" /fo TABLE /nh
schtasks /query /tn "ThrottleStop_NoUAC" /fo TABLE /nh

echo.
echo ============================================================
echo   Setup complete. Reboot to test.
echo ============================================================
pause
exit /b 0
