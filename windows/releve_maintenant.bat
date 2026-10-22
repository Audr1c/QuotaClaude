@echo off
REM Double-clic : fait un releve tout de suite, lance les tests, puis ouvre le widget.
cd /d "%~dp0.."
python claude_usage.py
echo.
python test_claude_usage.py
start "" pythonw server.py --open
pause
