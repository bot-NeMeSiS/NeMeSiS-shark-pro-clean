@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_nemesis_local.ps1"
timeout /t 3 /nobreak >nul
