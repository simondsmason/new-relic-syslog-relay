# Install syslog relay as Windows service using nssm
# Requires nssm to be installed (download from https://nssm.cc/)

Write-Host "Installing syslog relay as Windows service..." -ForegroundColor Green

# Path to the current directory and Python script
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptPath "syslog_relay.py"

# Service name
$serviceName = "SyslogRelay"

# Check if nssm is available
$nssmPath = "nssm.exe"
if (-not (Get-Command $nssmPath -ErrorAction SilentlyContinue)) {
    Write-Host "nssm not found. Please download from https://nssm.cc/ and add to PATH" -ForegroundColor Red
    exit 1
}

# Remove existing service if it exists
Write-Host "Removing existing service if present..." -ForegroundColor Yellow
& $nssmPath remove $serviceName confirm

# Install the service
Write-Host "Installing service..." -ForegroundColor Yellow
& $nssmPath install $serviceName python.exe $pythonScript
& $nssmPath set $serviceName AppDirectory $scriptPath
& $nssmPath set $serviceName Description "Syslog relay for timezone correction"
& $nssmPath set $serviceName Start SERVICE_AUTO_START

# Start the service
Write-Host "Starting service..." -ForegroundColor Yellow
Start-Service $serviceName

Write-Host "Service installed and started successfully!" -ForegroundColor Green
Write-Host "Service name: $serviceName" -ForegroundColor Cyan
Write-Host "To manage: services.msc or 'sc start/stop $serviceName'" -ForegroundColor Cyan 