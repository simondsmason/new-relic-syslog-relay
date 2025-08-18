# Check syslog relay status
Write-Host "=== Syslog Relay Status Check ===" -ForegroundColor Cyan

# Check Python processes
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    Write-Host "✅ Python processes found:" -ForegroundColor Green
    $pythonProcesses | ForEach-Object {
        Write-Host "  - PID: $($_.Id), CPU: $($_.CPU), Memory: $([math]::Round($_.WorkingSet/1MB, 1))MB" -ForegroundColor White
    }
} else {
    Write-Host "❌ No Python processes found" -ForegroundColor Red
}

# Check if port 513 is listening
$port513 = netstat -an | Select-String ":513"
if ($port513) {
    Write-Host "✅ Port 513 is listening:" -ForegroundColor Green
    $port513 | ForEach-Object { Write-Host "  - $_" -ForegroundColor White }
} else {
    Write-Host "❌ Port 513 is not listening" -ForegroundColor Red
}

# Check if port 514 is listening (ktranslate)
$port514 = netstat -an | Select-String ":514"
if ($port514) {
    Write-Host "✅ Port 514 is listening (ktranslate):" -ForegroundColor Green
    $port514 | ForEach-Object { Write-Host "  - $_" -ForegroundColor White }
} else {
    Write-Host "❌ Port 514 is not listening" -ForegroundColor Red
}

# Check Docker containers
Write-Host "`n=== Docker Containers ===" -ForegroundColor Cyan
$containers = docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
Write-Host $containers -ForegroundColor White

Write-Host "`n=== Summary ===" -ForegroundColor Cyan
if ($pythonProcesses -and $port513) {
    Write-Host "✅ Syslog relay appears to be running" -ForegroundColor Green
} else {
    Write-Host "❌ Syslog relay is NOT running" -ForegroundColor Red
    Write-Host "To start: .\start_relay_service.ps1" -ForegroundColor Yellow
} 