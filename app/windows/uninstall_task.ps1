# Removes the scheduled tasks "Claude Usage Tracker" and "Claude Usage Server".
# Called by run.py: powershell -NoProfile -ExecutionPolicy Bypass -File windows\uninstall_task.ps1
# The data folder is kept. Exit 0 on success (missing tasks are fine), 1 on error.
$ErrorActionPreference = "Stop"

$root  = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$names = @("Claude Usage Tracker", "Claude Usage Server")

try {
    foreach ($name in $names) {
        $task = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
        if ($task) {
            Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
            Unregister-ScheduledTask -TaskName $name -Confirm:$false
            Write-Host "Removed task '$name'."
        } else {
            Write-Host "Task '$name' not found (nothing to remove)."
        }
    }
    Write-Host "Uninstall complete. The data folder is kept: $root\data"
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

exit 0
