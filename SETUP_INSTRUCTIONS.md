# New Relic Syslog Relay Setup Instructions

## Overview
This system forwards syslog messages from your devices (Unraid, Hubitat, etc.) to New Relic with automatic timezone correction. The relay runs as a Windows service with a system tray icon for monitoring and control.

## Prerequisites
- Windows 10/11 with PowerShell
- Python 3.7+ installed and in PATH
- Docker Desktop installed (for ktranslate)
- New Relic account (US region)
- Admin access to create API keys in New Relic

## Required Python Packages
Install the required packages:
```powershell
pip install pystray pillow
```

## Step 1: New Relic Setup

### 1.1 Create New Relic Ingest API Key
1. Go to [New Relic API Keys](https://one.newrelic.com/api-keys)
2. Click "Create a key"
3. Select **Ingest - LICENSE** as the key type
4. Name it (e.g., "Syslog Forwarder")
5. **Copy and save the full key immediately!** (You won't be able to see it again)
6. Note your New Relic **Account ID** (visible in the UI)

### 1.2 Configure ktranslate
1. Edit `snmp-base.yaml` if needed (default configuration should work)
2. Run ktranslate Docker container:
```powershell
docker run -d --name ktranslate-syslog `
  --restart unless-stopped --pull=always `
  -p 514:5143/udp `
  -v "${PWD}/snmp-base.yaml:/snmp-base.yaml" `
  -e NEW_RELIC_API_KEY=YOUR_LICENSE_KEY `
  kentik/ktranslate:v2 `
  -snmp /snmp-base.yaml `
  -nr_account_id=YOUR_ACCOUNT_ID `
  -tee_logs=true `
  -service_name=syslog `
  nr1.syslog
```

## Step 2: Syslog Relay Installation

### 2.1 Configure Device IPs (Optional)
If you need timezone correction, edit `syslog_relay_tray.py` and update the `DEVICE_OFFSETS` dictionary:
```python
DEVICE_OFFSETS = {
    '192.168.2.110': 5,  # Unraid: +5 hours
    '192.168.2.108': 1,  # Hubitat: +1 hour
    # Add your device IPs and timezone offsets
}
```

### 2.2 Install as Scheduled Task (Recommended)
This method starts the relay automatically on Windows startup with a system tray icon:
```powershell
.\create_scheduled_task.ps1
```

### 2.3 Alternative: Install as Windows Service
If you prefer a Windows service without tray icon:
```powershell
.\install_as_service.ps1
```

### 2.4 Alternative: Install with nssm (Advanced)
If you have nssm installed and want more control:
```powershell
.\install_windows_service.ps1
```

## Step 3: Configure Your Devices

### 3.1 Unraid Configuration
1. Go to Settings → Syslog Server
2. Set Syslog Server to your Windows machine's IP address
3. Set Port to `513`
4. Enable syslog forwarding

### 3.2 Hubitat Configuration
1. Go to Settings → System → Logging
2. Set Syslog Server to your Windows machine's IP address
3. Set Port to `513`
4. Enable syslog forwarding

### 3.3 Other Devices
Configure any other devices to send syslog to your Windows machine's IP address on port `513`.

## Step 4: Verification and Testing

### 4.1 Check Relay Status
```powershell
.\check_relay_status.ps1
```

### 4.2 Test Message Flow
1. Check that port 513 is listening (should show in status check)
2. Check that port 514 is listening (ktranslate container)
3. Send a test message from one of your devices
4. Verify the message appears in New Relic

### 4.3 System Tray Icon
If using the scheduled task method:
- Look for a green circle icon in your system tray
- Right-click for options: Status, Stop, Restart
- The icon shows message count and last message time

## Step 5: Monitoring and Management

### 5.1 Check Logs
- **Scheduled Task**: Check Windows Event Viewer → Windows Logs → Application
- **Windows Service**: Check services.msc or use `Get-Service SyslogRelay`
- **Docker**: `docker logs ktranslate-syslog`

### 5.2 Start/Stop Commands
```powershell
# Scheduled Task
Start-ScheduledTask -TaskName "SyslogRelay"
Stop-ScheduledTask -TaskName "SyslogRelay"

# Windows Service
Start-Service SyslogRelay
Stop-Service SyslogRelay

# Docker
docker start ktranslate-syslog
docker stop ktranslate-syslog
```

### 5.3 Remove Installation
```powershell
# Remove scheduled task
Unregister-ScheduledTask -TaskName "SyslogRelay" -Confirm:$false

# Remove Windows service
sc.exe delete SyslogRelay

# Remove Docker container
docker rm -f ktranslate-syslog
```

## Troubleshooting

### Common Issues

1. **Port 513 not listening**
   - Check if relay is running: `.\check_relay_status.ps1`
   - Restart the relay service

2. **Port 514 not listening**
   - Check if ktranslate container is running: `docker ps`
   - Restart container: `docker restart ktranslate-syslog`

3. **Messages not appearing in New Relic**
   - Verify API key and account ID are correct
   - Check ktranslate logs: `docker logs ktranslate-syslog`
   - Verify network connectivity

4. **Timezone issues**
   - Update `DEVICE_OFFSETS` in `syslog_relay_tray.py`
   - Restart the relay service

5. **Python import errors**
   - Install required packages: `pip install pystray pillow`
   - Verify Python is in PATH

### Log Locations
- **Relay logs**: Windows Event Viewer → Application
- **ktranslate logs**: `docker logs ktranslate-syslog`
- **New Relic**: Check your New Relic dashboard for incoming logs

## File Structure
```
New Relic - Syslog/
├── syslog_relay_tray.py          # Main application with tray icon
├── syslog_relay.py               # Core relay functionality
├── snmp-base.yaml               # ktranslate configuration
├── syslog-ng.conf               # Docker relay configuration
├── create_scheduled_task.ps1    # Install as scheduled task
├── install_as_service.ps1       # Install as Windows service
├── install_windows_service.ps1  # Install with nssm
├── check_relay_status.ps1       # Status monitoring
├── setup_syslog_relay.ps1       # Docker relay setup
├── ktranslate_newrelic_setup_instructions.txt  # Original setup guide
└── SETUP_INSTRUCTIONS.md        # This file
```

## Support
For issues or questions:
1. Check the troubleshooting section above
2. Review the original setup instructions in `ktranslate_newrelic_setup_instructions.txt`
3. Check New Relic documentation for syslog integration 