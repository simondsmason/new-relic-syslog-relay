# Update desktop shortcut for Syslog Relay with current version
$WshShell = New-Object -comObject WScript.Shell

# Remove old shortcut if it exists
$oldShortcut = "$env:USERPROFILE\Desktop\Syslog Relay.lnk"
if (Test-Path $oldShortcut) {
    Remove-Item $oldShortcut -Force
    Write-Host "Removed old desktop shortcut"
}

# Create new shortcut with current version
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Syslog Relay.lnk")
$Shortcut.TargetPath = "$PSScriptRoot\start_syslog_relay.bat"
$Shortcut.WorkingDirectory = "$PSScriptRoot"
$Shortcut.Description = "Start Syslog Relay v1.07"
$Shortcut.IconLocation = "$PSScriptRoot\syslog_relay_tray.py,0"
$Shortcut.Save()

Write-Host "Desktop shortcut updated successfully to v1.07!"
Write-Host "You can now double-click 'Syslog Relay' on your desktop to start the relay." 