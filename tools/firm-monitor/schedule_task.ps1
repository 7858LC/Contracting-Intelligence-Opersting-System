# schedule_task.ps1 — registers a weekly Windows Scheduled Task that runs
# monitor.py every Monday morning. Per-user task, no admin rights required.
#
# Usage: powershell -ExecutionPolicy Bypass -File schedule_task.ps1

$taskName = "CIOS Firm Monitor - Weekly USASpending Check"
$scriptDir = $PSScriptRoot
$pythonExe = (Get-Command python).Source

$action = New-ScheduledTaskAction -Execute $pythonExe -Argument "monitor.py" -WorkingDirectory $scriptDir
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 7am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "Weekly check of CIOS target firm list against USASpending.gov for new/modified federal awards." -Force

Write-Output "Registered scheduled task: $taskName (Mondays 7:00 AM, runs monitor.py in $scriptDir)"
