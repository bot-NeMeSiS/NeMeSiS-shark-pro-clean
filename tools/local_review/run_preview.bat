@echo off
setlocal
set "PYTHON=%~dp0..\..\.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=%USERPROFILE%\.codex\visualizations\2026\05\27\019e69a5-0d06-7af3-98c9-b9e23032ef02\reconcile-r10-20260913\retained-before-main\.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
  echo No se encuentra el Python preparado para NeMeSiS. No se ha instalado ni cambiado nada.
  exit /b 1
)
"%PYTHON%" -B "%~dp0preview.py" %*
exit /b %ERRORLEVEL%
