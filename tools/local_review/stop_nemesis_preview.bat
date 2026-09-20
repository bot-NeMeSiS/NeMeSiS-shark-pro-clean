@echo off
call "%~dp0run_preview.bat" stop %*
if errorlevel 1 pause
