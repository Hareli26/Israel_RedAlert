@echo off
:: Change to the directory where THIS bat file lives
cd /d "%~dp0"
chcp 65001 > nul
title Red Alert - התרעות צבע אדום

echo.
echo  ===================================
echo   Red Alert Monitor v2.0
echo   Powered by Pikud HaOref API
echo  ===================================
echo.

set PYTHON_CMD=

:: Try py launcher first (Windows Python Launcher)
py --version > nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py
    goto :found
)

:: Try python
python --version > nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python
    goto :found
)

:: Try python3
python3 --version > nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python3
    goto :found
)

echo  ERROR: Python not found in PATH
echo  Please restart this batch file after Python installation completes.
echo  Or open a NEW command prompt and run:   py red_alert.py
pause
exit /b 1

:found
echo  Python found: %PYTHON_CMD%
echo  Installing dependencies...
echo.

%PYTHON_CMD% -m pip install PyQt5 PyQtWebEngine requests --quiet --upgrade

if errorlevel 1 (
    echo.
    echo  pip failed - trying without upgrade flag...
    %PYTHON_CMD% -m pip install PyQt5 requests
)

echo.
echo  Starting Red Alert Monitor...
echo.

%PYTHON_CMD% red_alert.py

if errorlevel 1 (
    echo.
    echo  ERROR: Application crashed. Check errors above.
    pause
)
