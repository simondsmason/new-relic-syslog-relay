# Create desktop shortcut for Syslog Relay
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Syslog Relay.lnk")
$Shortcut.TargetPath = "$PSScriptRoot\start_syslog_relay.bat"
$Shortcut.WorkingDirectory = "$PSScriptRoot"
$Shortcut.Description = "Start Syslog Relay v1.04"
$Shortcut.IconLocation = "$PSScriptRoot\syslog_relay_tray.py,0"
$Shortcut.Save()

Write-Host "Desktop shortcut created successfully!"
Write-Host "You can now double-click 'Syslog Relay' on your desktop to start the relay." 