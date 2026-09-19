@echo off
call "%~dp0run_preview.bat" start %*
if errorlevel 1 pause
