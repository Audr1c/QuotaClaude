@echo off
REM Supprime les taches planifiees (les donnees dans data\ sont conservees).
cd /d "%~dp0.."
schtasks /Delete /TN "Claude Usage Tracker" /F 2>nul
schtasks /Delete /TN "Claude Usage Server" /F 2>nul
echo Taches supprimees (si elles existaient). Le dossier data\ est conserve.
pause
