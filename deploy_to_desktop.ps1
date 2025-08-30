# Deploy Syslog Relay files to Desktop folder
# This script copies the necessary files to the desktop folder for better performance

$desktopPath = "$env:USERPROFILE\Desktop\Syslog Relay"
$sourcePath = $PSScriptRoot

Write-Host "Deploying Syslog Relay files to Desktop..." -ForegroundColor Green
Write-Host "Source: $sourcePath" -ForegroundColor Yellow
Write-Host "Destination: $desktopPath" -ForegroundColor Yellow

# Create destination directory if it doesn't exist
if (!(Test-Path $desktopPath)) {
    New-Item -ItemType Directory -Path $desktopPath -Force
    Write-Host "Created directory: $desktopPath" -ForegroundColor Green
}

# Files to copy
$filesToCopy = @(
    "syslog_relay_tray.py",
    "start_syslog_relay.bat", 
    "requirements.txt"
)

# Copy each file
foreach ($file in $filesToCopy) {
    $sourceFile = Join-Path $sourcePath $file
    $destFile = Join-Path $desktopPath $file
    
    if (Test-Path $sourceFile) {
        Copy-Item -Path $sourceFile -Destination $destFile -Force
        Write-Host "Copied: $file" -ForegroundColor Green
    } else {
        Write-Host "Warning: Source file not found: $file" -ForegroundColor Yellow
    }
}

Write-Host "`nDeployment complete!" -ForegroundColor Green
Write-Host "Files are now available in: $desktopPath" -ForegroundColor Cyan
Write-Host "You can now run the relay from the desktop folder for better performance." -ForegroundColor Cyan

