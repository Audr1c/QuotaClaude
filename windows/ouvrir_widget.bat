@echo off
REM Ouvre le widget dans le navigateur. Le serveur tourne en arriere-plan, sans fenetre
REM (pythonw) ; s'il tourne deja, la commande ouvre seulement le navigateur et s'arrete.
cd /d "%~dp0.."
start "" pythonw server.py --open
