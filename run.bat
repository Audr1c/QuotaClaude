@echo off
rem Windows launcher: finds Python 3.8+ and starts the interactive menu.
rem Double-click this file, or run it from a terminal: run.bat [command]
cd /d "%~dp0"
set "PY="
py -3 -c "import sys" >nul 2>nul && set "PY=py -3"
if not defined PY python -c "import sys" >nul 2>nul && set "PY=python"
if not defined PY (
    echo Python 3.8 or newer was not found.
    echo Install it from https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^) and run this file again.
    pause
    exit /b 1
)
%PY% run.py %*
if errorlevel 1 pause
