# Install syslog relay as Windows service
Write-Host "Installing syslog relay as Windows service..." -ForegroundColor Green

# Get current directory and script path
$currentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $currentDir "syslog_relay_tray.py"

# Service name
$serviceName = "SyslogRelay"

Write-Host "Current directory: $currentDir" -ForegroundColor Yellow
Write-Host "Python script: $pythonScript" -ForegroundColor Yellow
Write-Host "Service name: $serviceName" -ForegroundColor Yellow

# Check if service already exists
$existingService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Host "Removing existing service..." -ForegroundColor Yellow
    Stop-Service $serviceName -Force -ErrorAction SilentlyContinue
    sc.exe delete $serviceName
}

# Create the service
Write-Host "Creating service..." -ForegroundColor Yellow
$binPath = "`"$env:PYTHONPATH\python.exe`" `"$pythonScript`""
sc.exe create $serviceName binPath= $binPath start= auto DisplayName= "Syslog Relay Service"

# Set service description
sc.exe description $serviceName "Syslog relay for timezone correction and forwarding to New Relic"

# Start the service
Write-Host "Starting service..." -ForegroundColor Yellow
Start-Service $serviceName

Write-Host "✅ Service installed and started successfully!" -ForegroundColor Green
Write-Host "Service name: $serviceName" -ForegroundColor Cyan
Write-Host "To manage: services.msc or 'sc start/stop $serviceName'" -ForegroundColor Cyan
Write-Host "To remove: sc.exe delete $serviceName" -ForegroundColor Yellow 