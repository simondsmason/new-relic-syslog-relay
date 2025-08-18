# Syslog Relay Setup Script
# This script sets up a syslog-ng relay to fix timezone issues before forwarding to ktranslate

Write-Host "Setting up syslog-ng relay..." -ForegroundColor Green

# Stop and remove existing relay if it exists
Write-Host "Removing existing syslog-relay container..." -ForegroundColor Yellow
docker rm -f syslog-relay 2>$null

# Start syslog-ng relay container
Write-Host "Starting syslog-ng relay on port 513..." -ForegroundColor Yellow
docker run -d --name syslog-relay --restart unless-stopped `
  -p 513:514/udp `
  -v "${PWD}/syslog-ng.conf:/etc/syslog-ng/syslog-ng.conf" `
  balabit/syslog-ng:latest

# Check if relay started successfully
Write-Host "Checking relay status..." -ForegroundColor Yellow
Start-Sleep -Seconds 3
docker ps --filter name=syslog-relay

Write-Host "`nSetup complete!" -ForegroundColor Green
Write-Host "Now configure your devices to send syslog to port 513:" -ForegroundColor Cyan
Write-Host "- Unraid: Set syslog server to your host IP, port 513" -ForegroundColor White
Write-Host "- Hubitat: Set syslog server to your host IP, port 513" -ForegroundColor White
Write-Host "`nThe relay will automatically adjust timestamps and forward to ktranslate on port 514." -ForegroundColor Cyan 