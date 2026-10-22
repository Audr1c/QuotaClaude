# Installs the periodic reading as the scheduled task "Claude Usage Tracker".
# With -WithServer, also installs "Claude Usage Server" (widget server, starts at logon); without it, that task is removed.
# Called by run.py: powershell -NoProfile -ExecutionPolicy Bypass -File windows\install_task.ps1 -Minutes N [-WithServer] -PythonW "C:\path\pythonw.exe"
param(
    [int]$Minutes = 10,
    [switch]$WithServer,
    [string]$PythonW = ""
)

$ErrorActionPreference = "Stop"

$root   = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$script = Join-Path $root "claude_usage.py"
$server = Join-Path $root "server.py"

function New-TaskSettings([TimeSpan]$TimeLimit) {
    New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit $TimeLimit
}

try {
    if ($Minutes -lt 1 -or $Minutes -gt 1439) {
        throw "Minutes must be between 1 and 1439 (got $Minutes)."
    }

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

    # Periodic reading: first run one minute from now, then every $Minutes minutes.
    $action   = New-ScheduledTaskAction -Execute $interpreter -Argument "`"$script`"" -WorkingDirectory $root
    $trigger  = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes $Minutes)
    $settings = New-TaskSettings -TimeLimit (New-TimeSpan -Minutes 2)
    Register-ScheduledTask -TaskName "Claude Usage Tracker" -Action $action -Trigger $trigger -Settings $settings -Description "Claude quota reading (5 h / 7 d) into $root\data" -Force | Out-Null

    Write-Host "Task 'Claude Usage Tracker' installed: one reading every $Minutes minutes."
    Write-Host "Log: $root\data\tracker.log"

    # Widget server: optional, starts at logon.
    if ($WithServer) {
        $sAction   = New-ScheduledTaskAction -Execute $interpreter -Argument "`"$server`"" -WorkingDirectory $root
        $sTrigger  = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
        $sSettings = New-TaskSettings -TimeLimit ([TimeSpan]::Zero)
        Register-ScheduledTask -TaskName "Claude Usage Server" -Action $sAction -Trigger $sTrigger -Settings $sSettings -Description "Local server for the Claude Usage widget (127.0.0.1)" -Force | Out-Null
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
