# Installs the adaptive poller as the scheduled task "Claude Usage Tracker" (starts at logon, started now).
# With -WithServer, also installs "Claude Usage Server" (widget server, starts at logon); without it, that task is removed.
# Called by run.py: powershell -NoProfile -ExecutionPolicy Bypass -File windows\install_task.ps1 [-WithServer] -PythonW "C:\path\pythonw.exe"
param(
    [switch]$WithServer,
    [string]$PythonW = ""
)

$ErrorActionPreference = "Stop"

$root   = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$poller = Join-Path $root "poller.py"
$server = Join-Path $root "server.py"

function New-TaskSettings {
    # no time limit; restarted if it ever crashes
    New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew `
        -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1)
}

function Restart-Task([string]$Name) {
    Stop-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
    Start-ScheduledTask -TaskName $Name
}

try {
    # Interpreter: -PythonW if it exists, otherwise pythonw.exe from PATH (Microsoft Store alias excluded).
    $interpreter = $null
    if ($PythonW -ne "") {
        if (Test-Path -LiteralPath $PythonW -PathType Leaf) {
            $interpreter = (Resolve-Path -LiteralPath $PythonW).Path
        } else {
            Write-Host "WARNING: -PythonW not found: $PythonW. Looking for pythonw.exe on PATH." -ForegroundColor Yellow
        }
    }
    if (-not $interpreter) {
        $found = Get-Command pythonw -ErrorAction SilentlyContinue | Where-Object { $_.Source -notlike "*WindowsApps*" } | Select-Object -First 1
        if ($found) { $interpreter = $found.Source }
    }
    if (-not $interpreter) {
        throw "pythonw.exe not found (Microsoft Store alias excluded). Pass -PythonW or add Python to PATH."
    }
    Write-Host "Interpreter: $interpreter"

    # Adaptive poller: one long-running process per session (it picks its own timing: 30 s to 10 min).
    # Replaces the fixed-interval trigger of older versions.
    $action  = New-ScheduledTaskAction -Execute $interpreter -Argument "`"$poller`"" -WorkingDirectory $root
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    Stop-ScheduledTask -TaskName "Claude Usage Tracker" -ErrorAction SilentlyContinue
    Register-ScheduledTask -TaskName "Claude Usage Tracker" -Action $action -Trigger $trigger -Settings (New-TaskSettings) -Description "Claude quota readings (5 h / 7 d), adaptive timing, into $root\data" -Force | Out-Null
    Restart-Task "Claude Usage Tracker"

    Write-Host "Task 'Claude Usage Tracker' installed: adaptive poller, starts at logon (started now)."
    Write-Host "Log: $root\data\tracker.log"

    # Widget server: optional, starts at logon.
    if ($WithServer) {
        $sAction  = New-ScheduledTaskAction -Execute $interpreter -Argument "`"$server`"" -WorkingDirectory $root
        $sTrigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
        Register-ScheduledTask -TaskName "Claude Usage Server" -Action $sAction -Trigger $sTrigger -Settings (New-TaskSettings) -Description "Local server for the Claude Usage widget (127.0.0.1)" -Force | Out-Null
        Start-ScheduledTask -TaskName "Claude Usage Server"
        Write-Host "Task 'Claude Usage Server' installed: starts at logon (started now)."
    } else {
        if (Get-ScheduledTask -TaskName "Claude Usage Server" -ErrorAction SilentlyContinue) {
            Stop-ScheduledTask -TaskName "Claude Usage Server" -ErrorAction SilentlyContinue
            Unregister-ScheduledTask -TaskName "Claude Usage Server" -Confirm:$false
        }
        Write-Host "Widget server task not installed (or removed)."
    }
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

exit 0
