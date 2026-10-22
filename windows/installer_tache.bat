@echo off
REM Double-clic : installe le releve automatique toutes les 10 minutes.
REM Avec un argument, installer_tache.bat -AvecServeur lance aussi le serveur du widget a l'ouverture de session.
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer_tache.ps1" %*
pause
