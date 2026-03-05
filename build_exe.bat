@echo off
cd /d "%~dp0"
echo.
echo  =======================================
echo   Red Alert - Build EXE
echo  =======================================
echo.

set PYTHON_CMD=
py --version > nul 2>&1
if not errorlevel 1 (set PYTHON_CMD=py) else (
  python --version > nul 2>&1
  if not errorlevel 1 (set PYTHON_CMD=python)
)
if "%PYTHON_CMD%"=="" (echo ERROR: Python not found & pause & exit /b 1)

echo Installing PyInstaller...
%PYTHON_CMD% -m pip install pyinstaller --quiet

echo Building EXE (this takes 1-2 minutes)...
%PYTHON_CMD% -m PyInstaller ^
  --onefile ^
  --windowed ^
  --name "RedAlertMonitor" ^
  --hidden-import PyQt5.QtWebEngineWidgets ^
  --hidden-import PyQt5.QtWebEngineCore ^
  --hidden-import requests ^
  red_alert.py

if exist "dist\RedAlertMonitor.exe" (
    echo.
    echo  SUCCESS!
    echo  EXE is at:  dist\RedAlertMonitor.exe
    echo.
    echo  Copy RedAlertMonitor.exe to wherever you want,
    echo  then run it - it will prompt for admin rights.
    explorer dist
) else (
    echo.
    echo  Build failed. Check errors above.
)
pause
