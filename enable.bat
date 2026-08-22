@echo off
chcp 65001 >nul
:: LegionOptimization — 一键启用 (Enable) 快捷入口，双击自动提权
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0enable.ps1"
pause
