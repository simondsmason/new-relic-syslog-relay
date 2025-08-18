# Create scheduled task for syslog relay
Write-Host "Creating scheduled task for syslog relay..." -ForegroundColor Green

# Get current directory and script path
$currentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $currentDir "syslog_relay_tray.py"

# Task name
$taskName = "SyslogRelay"

Write-Host "Current directory: $currentDir" -ForegroundColor Yellow
Write-Host "Python script: $pythonScript" -ForegroundColor Yellow
Write-Host "Task name: $taskName" -ForegroundColor Yellow

# Remove existing task if it exists
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Create action
$action = New-ScheduledTaskAction -Execute "python.exe" -Argument "`"$pythonScript`"" -WorkingDirectory $currentDir

# Create trigger (at startup)
$trigger = New-ScheduledTaskTrigger -AtStartup

# Create settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Create principal (run as current user)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

# Register the task
Write-Host "Creating scheduled task..." -ForegroundColor Yellow
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Syslog relay for timezone correction"

Write-Host "✅ Scheduled task created successfully!" -ForegroundColor Green
Write-Host "Task name: $taskName" -ForegroundColor Cyan
Write-Host "The syslog relay will now start automatically when Windows starts." -ForegroundColor Cyan
Write-Host "To manage: Task Scheduler (taskschd.msc)" -ForegroundColor Cyan
Write-Host "To remove: Unregister-ScheduledTask -TaskName $taskName" -ForegroundColor Yellow 