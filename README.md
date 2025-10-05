# New Relic Syslog Relay

A Windows syslog relay service for forwarding Hubitat and Docker container logs to New Relic.

## Overview

This project provides a syslog relay service that runs on Windows and forwards syslog messages from various sources (Hubitat devices, Docker containers, etc.) to New Relic for monitoring and analysis.

## Features

- **Syslog Relay**: Listens on UDP port 513 and forwards messages to ktranslate on port 514
- **Tray Application**: Runs as a system tray application with status monitoring
- **Automatic Log Rotation**: Maintains log files at manageable sizes
- **Timezone Adjustment**: Automatically adjusts timestamps based on source device
- **RFC 5424 to RFC 3164 Conversion**: Converts modern syslog format to legacy format for compatibility
- **Device-Specific Configuration**: Supports different timezone offsets for various devices

## Version History

### v1.07 (2025-08-03)
- Add process ID to message format for better identification

### v1.06 (2025-08-03)
- Add device name to message format for better identification

### v1.05 (2025-08-03)
- Remove dash and space stripping post-processing for cleaner message display

### v1.04 (2025-08-03)
- Fix RFC 5424 parsing to correctly assign hostname and app-name fields

### v1.03 (2025-08-03)
- Add detailed debug logging to log file for RFC 5424 parsing

### v1.02 (2025-08-03)
- Preserve original hostname in Hubitat RFC 5424 to RFC 3164 conversion

### v1.01 (2025-08-03)
- Strip leading dash and space from Hubitat messages for cleaner New Relic display

### v1.00 (2025-07-26)
- Initial version with detailed incoming/outgoing message logging

## Installation

### Prerequisites

- Python 3.7 or higher
- Windows 10/11
- New Relic account with ktranslate configured

### Setup

1. Clone this repository
2. Install required Python packages:
   ```bash
   pip install pystray pillow
   ```
3. Configure your device IPs and timezone offsets in `syslog_relay_tray.py`
4. Run the relay:
   ```bash
   python syslog_relay_tray.py
   ```

## Configuration

### Device Configuration

Edit the `DEVICE_OFFSETS` dictionary in `syslog_relay_tray.py` to configure your devices:

```python
DEVICE_OFFSETS = {
    '192.168.2.110': 5,  # Unraid: +5 hours
    '192.168.2.108': 5,  # Hubitat: +5 hours
    # Add your devices here
}
```

### Docker Integration

To forward Docker container logs, add this to your Docker run command:

```bash
--log-driver=syslog --log-opt syslog-address=udp://192.168.2.70:513 --log-opt tag="{{.Name}}"
```

**Syslog Relay Server:** `192.168.2.70:513`
- This is the IP address where the syslog relay is running
- All Docker containers and devices should send syslog to this address
- The relay forwards messages to ktranslate on port 514 for New Relic ingestion

## Usage

### Running as Tray Application

The relay runs as a system tray application with a green circle icon. Right-click the icon for options:
- **Status**: View current relay status and message count
- **Stop**: Stop the relay
- **Restart**: Restart the relay

### Console Output

When running, the relay displays real-time incoming and outgoing messages in the console window, making it easy to monitor message flow.

## Files

- `syslog_relay_tray.py` - Main relay application
- `setup_syslog_relay.ps1` - PowerShell setup script
- `install_as_service.ps1` - Install as Windows service
- `create_desktop_shortcut.ps1` - Create desktop shortcut
- `snmp-base.yaml` - ktranslate configuration template

## Troubleshooting

### Check if Relay is Receiving Messages

1. Look at the console output for incoming messages
2. Check the log file for detailed debug information
3. Verify your device is sending to the correct IP and port (513)

### Common Issues

- **No messages appearing**: Check firewall settings and ensure port 513 is open
- **Timezone issues**: Verify device offsets in the configuration
- **Large log files**: The relay now includes automatic log rotation

## License

MIT License - see LICENSE file for details.

## Author

Simon Mason
