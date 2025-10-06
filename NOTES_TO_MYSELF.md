# Notes to Myself

## Log File Storage and Management

The syslog relay stores detailed logs in the following location:

**Log Directory:** `C:\Users\simon\Desktop\Syslog Relay\`

**Log Files:**
- `syslog_relay.log` - Current active log file
- `syslog_relay.log.1` - Previous log file (rotated)
- `syslog_relay.log.2` - Older log file (rotated)
- `syslog_relay.log.3` - Even older log file (rotated)
- `syslog_relay.log.4` - Oldest log file (rotated)

**Log Rotation Settings:**
- Maximum log file size: 1 MB (defined in `MAX_LOG_SIZE`)
- Maximum number of log files: 5 (defined in `MAX_LOG_FILES`)
- When the current log exceeds 1 MB, it's rotated to `.1` and a new log file is created

**What's Logged:**
- **Incoming Messages**: Raw syslog messages received from devices/containers
- **Outgoing Messages**: Transformed messages sent to ktranslate
- **RFC 5424 Parsing Debug**: Detailed parsing information for Hubitat messages
- **System Stats**: Periodic system monitoring data
- **Startup/Shutdown Messages**: Relay lifecycle events

**Searching Logs:**
To search for specific container or device messages:
```powershell
# Search for immichFrame entries
Select-String -Path "C:\Users\simon\Desktop\Syslog Relay\syslog_relay.log*" -Pattern "immich" -CaseSensitive:$false

# Search for specific container ID
Select-String -Path "C:\Users\simon\Desktop\Syslog Relay\syslog_relay.log*" -Pattern "5183c0a146c0" -CaseSensitive:$false
```

**Docker Container Mapping:**
The relay uses a hardcoded mapping in `syslog_relay_tray.py` (lines 290-295) to convert Docker container IDs to friendly names:
```python
docker_container_mapping = {
    '5183c0a146c0': 'immichFrame-All',  # Add more mappings as needed
}
```

To add new containers, find their container ID using `docker ps` and add them to this mapping.

## Current Issue: immichFrame-test Not Working

**Problem:** The `immichFrame-test` container is not appearing in New Relic logs.

**Root Cause:** The container ID for `immichFrame-test` is not in the Docker container mapping.

**Solution:** 
1. Find the container ID of `immichFrame-test` using `docker ps`
2. Add it to the `docker_container_mapping` in `syslog_relay_tray.py`
3. Restart the relay

**Known Container IDs:**
- `5183c0a146c0` → `immichFrame-All` (working)
- `[TO BE DETERMINED]` → `immichFrame-test` (not working)

## Status Option Behavior

The "Status" option in the tray menu doesn't show visual feedback. It:
- Sends a health check message to ktranslate
- Logs the health check to the log files
- Appears in New Relic as a message from "syslog-relay"

This is working as designed - no popup or console output is shown.

## Version Updates and Deployment Workflow

**IMPORTANT:** The relay uses a two-folder system:

**Working Folder:** `C:\Users\simon\iCloudDrive\Documents\HA\Hubitat Code\Cursor Repositories\New Relic - Syslog\`
- Source code storage and version control
- All development and changes happen here

**Execution Folder:** `C:\Users\simon\Desktop\Syslog Relay\`
- Where the relay actually runs from
- Must be updated for changes to take effect

**Complete Deployment Process:**
1. **Update the code** in the working folder (iCloudDrive)
2. **Update version number** in `syslog_relay_tray.py` (VERSION variable)
3. **Update version number** in `start_syslog_relay.bat` (title and echo messages) ⚠️ **CRITICAL: Don't forget this step!**
4. **Add changelog entry** for the new version in `CHANGELOG` dictionary
5. **Commit changes to git:**
   ```powershell
   git add .
   git commit -m "Version X.XX: Description of changes"
   git push origin main
   ```
6. **Deploy to execution folder:**
   ```powershell
   .\deploy_to_desktop.ps1
   ```
7. **Restart the relay** to run the new version

**Why This Two-Folder System:**
- iCloudDrive folder provides version control and backup
- Desktop folder provides better performance for running applications
- Changes don't automatically apply - must be deployed
- The deployment script automates the copy process

**Note:** The GitHub README.md contains the changelog, not this notes file.

## Hubitat Dual Send Mode (Version 1.30+)

**Purpose:** Send both converted RFC 3164 and original RFC 5424 messages for Hubitat devices to solve the `app_name` field parsing issue in New Relic.

**Configuration:** `HUBITAT_DUAL_SEND_MODE = True` in `syslog_relay_tray.py`

**How It Works:**
- For Hubitat RFC 5424 messages only (detected by `is_hubitat_rfc5424_message()`)
- Sends converted RFC 3164 message (existing behavior for timestamp display)
- Sends original RFC 5424 message (new behavior for proper `app_name` field parsing)
- Other devices (Docker, etc.) are unaffected

**Result in New Relic:**
- Two entries for each Hubitat message:
  1. Converted RFC 3164: `HVAC_.Conservatory.Floor.Second.Sensor: HVAC_.Conservatory.Floor.Second.Sensor (7523) - HVAC: Conservatory Floor...`
  2. Original RFC 5424: `HVAC_.Conservatory.Floor.Second.Sensor` (proper `app_name` field)

**Logging:** Dual send messages are logged as "hubitat_dual_send_original" in the log files.

## Syslog Message Format Processing

The relay processes two different syslog message formats differently:

### RFC 5424 Format (GETS REFORMATTED)
- **Pattern**: `<priority>1 timestamp hostname app-name process-id message-id structured-data message`
- **Example**: `<14>1 2025-09-21T19:28:07.858-04:00 HubitatC8Pro-2 A/V:.CHA3... 1313 - - Action: ...`
- **Sources**: Hubitat devices (HubitatC8Pro-2, HubitatC7, HubitatC8Pro, etc.)
- **Processing**: **Full reformatting** from RFC 5424 to RFC 3164
  - Timezone adjustment (+5 hours for local timezone)
  - Format conversion to traditional syslog
  - App name cleaning (removes special characters, HTML tags)
  - Enhanced structure with process ID included
  - Output format: `<priority>timestamp hostname app-name: app-name (process-id) - message`

### RFC 3164 Format (PASSED THROUGH WITH MINIMAL PROCESSING)
- **Pattern**: `<priority>Month Day HH:MM:SS hostname message`
- **Example**: `<134>Sep 21 19:28:07 some-device message content`
- **Sources**: Traditional syslog devices, Docker containers, other systems
- **Processing**: **Minimal processing** - only timestamp adjustment
  - Timezone offset applied (+5 hours)
  - Message structure preserved
  - Passed through largely unchanged

### Unknown Formats (PASSED THROUGH UNCHANGED)
- **Processing**: No modifications at all
- **Behavior**: Message forwarded exactly as received

### Message Fields Extracted from RFC 5424:
1. **Priority** (`<14>`) - Syslog priority/facility level
2. **Version** (`1`) - RFC 5424 version number  
3. **Timestamp** (`2025-09-21T19:28:07.858-04:00`) - ISO 8601 format with timezone
4. **Hostname** (`HubitatC8Pro-2`, `HubitatC7`) - Source device hostname
5. **App-name** (`A/V:.CHA3.-.Cover.Art.Changes.-.Perform.Actions`) - Application/service name
6. **Process-ID** (`1313`, `278`) - Process identifier
7. **Message-ID** (`-`) - Usually dash for no message ID
8. **Structured-Data** (`-`) - Usually dash for no structured data
9. **Message Content** - The actual log message

### Processing Logic Location in Code:
- **Lines 237-328**: RFC 5424 detection and full reformatting
- **Lines 335-362**: RFC 3164 detection and timestamp adjustment only
- **Line 368**: Fallback - pass through unchanged if no pattern matches
