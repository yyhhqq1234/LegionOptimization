@echo off
chcp 65001 >nul
:: LegionOptimization — 一键禁用 (Disable) 快捷入口，双击自动提权
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0disable.ps1"
pause
