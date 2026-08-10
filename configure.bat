@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ============================================================
:: LegionOptimization — Configure for current install path
:: Run this after moving the project folder to update all
:: hardcoded paths in LenovoLegionToolkit's automation.json
:: ============================================================

set "SCRIPT_DIR=%~dp0"
set "AUTO_JSON=%LOCALAPPDATA%\LenovoLegionToolkit\automation.json"

echo ============================================================
echo   LegionOptimization — Path Configuration
echo ============================================================
echo.
echo Project directory: %SCRIPT_DIR%
echo automation.json : %AUTO_JSON%
echo.

if not exist "%AUTO_JSON%" (
    echo [WARNING] automation.json not found.
    echo LLT may not be set up yet. Run setup_startup.bat first.
    echo.
    echo Creating a template automation.json...
    goto :create_template
)

echo Updating batch script paths in automation.json...

:: Use PowerShell to update JSON paths
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    $json = Get-Content -Path '%AUTO_JSON%' -Raw -Encoding UTF8; ^
    $json = $json -replace 'D:\\LegionOptimization', '%SCRIPT_DIR:\=\\%'; ^
    $json = $json -replace 'D:/LegionOptimization', '%SCRIPT_DIR:\=/%'; ^
    Set-Content -Path '%AUTO_JSON%' -Value $json -Encoding UTF8 -NoNewline

if %errorlevel% equ 0 (
    echo [OK] automation.json updated.
) else (
    echo [FAILED] Could not update automation.json.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Configuration complete.
echo   Reboot to apply all changes.
echo ============================================================
pause
exit /b 0

:create_template
echo.
echo You'll need to import the automation.json template from:
echo   %SCRIPT_DIR%automation.template.json
echo into Lenovo Legion Toolkit (Settings ^> Automation ^> Import).
echo Then re-run this configure.bat.
pause
exit /b 1
