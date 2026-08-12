@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0\..\.."
set "NEMESIS_MODE=%~1"
if "%NEMESIS_MODE%"=="" set "NEMESIS_MODE=offline_safe"
set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
  where python >nul 2>nul || (
    echo No se encontro Python ni el entorno .venv de NeMeSiS.
    echo La carpeta oficial necesita sus dependencias locales antes de arrancar.
    pause
    exit /b 1
  )
  set "PYTHON_EXE=python"
)
"%PYTHON_EXE%" "tools\local_desktop\run_local_desktop.py" --mode %NEMESIS_MODE%
if errorlevel 1 (
  timeout /t 2 /nobreak >nul
  if not exist "%CD%\data\local_dev\nemesis_local.pid.json" exit /b 0
  echo.
  echo NeMeSiS LOCAL no pudo arrancar. Revisa el mensaje anterior.
  pause
)
endlocal