# Cree les taches planifiees Windows pour Claude Usage Tracker.
# - "Claude Usage Tracker" : un releve toutes les N minutes (defaut 10).
# - "Claude Usage Server" (avec -AvecServeur) : le serveur du widget, lance a l'ouverture de session.
# (Windows n'a pas cron : le Planificateur de taches joue le meme role.)
param(
    [int]$Minutes = 10,
    [switch]$AvecServeur
)

$root   = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$script = Join-Path $root "claude_usage.py"
$server = Join-Path $root "server.py"

$py = Get-Command pythonw -ErrorAction SilentlyContinue | Where-Object { $_.Source -notlike "*WindowsApps*" } | Select-Object -First 1
if (-not $py) {
    Write-Host "pythonw.exe introuvable (hors alias Microsoft Store). Installe Python ou ajoute-le au PATH." -ForegroundColor Red
    exit 1
}
Write-Host "Python utilise : $($py.Source)"

# Releve periodique
$action   = New-ScheduledTaskAction -Execute $py.Source -Argument "`"$script`"" -WorkingDirectory $root
$trigger  = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes $Minutes)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
            -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 2)

Register-ScheduledTask -TaskName "Claude Usage Tracker" -Action $action -Trigger $trigger -Settings $settings `
    -Description "Releve du quota Claude (5 h / 7 j) dans $root\data" -Force | Out-Null

Write-Host "Tache 'Claude Usage Tracker' installee : un releve toutes les $Minutes minutes." -ForegroundColor Green
Write-Host "Journal : $root\data\tracker.log"

# Serveur du widget (optionnel)
if ($AvecServeur) {
    $sAction   = New-ScheduledTaskAction -Execute $py.Source -Argument "`"$server`"" -WorkingDirectory $root
    $sTrigger  = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $sSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
                 -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero)

    Register-ScheduledTask -TaskName "Claude Usage Server" -Action $sAction -Trigger $sTrigger -Settings $sSettings `
        -Description "Serveur local du widget Claude Usage (http://127.0.0.1:8765/)" -Force | Out-Null
    Start-ScheduledTask -TaskName "Claude Usage Server"

    Write-Host "Tache 'Claude Usage Server' installee : demarre a l'ouverture de session." -ForegroundColor Green
    Write-Host "Widget : http://127.0.0.1:8765/"
}
