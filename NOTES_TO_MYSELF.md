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

## Version Updates and Local Folder Management

**IMPORTANT:** When creating new versions of the relay, remember to update the local execution folder:

**Working Folder:** `C:\Users\simon\iCloudDrive\Documents\HA\Hubitat Code\Cursor Repositories\New Relic - Syslog\`
**Execution Folder:** `C:\Users\simon\Desktop\Syslog Relay\`

**Required Steps for Each Version Update:**
1. Update the code in the working folder (iCloudDrive)
2. Update version number in `syslog_relay_tray.py` (VERSION variable)
3. Update version number in `start_syslog_relay.bat` (title and echo messages)
4. Add changelog entry for the new version
5. **Copy updated files to execution folder:**
   ```powershell
   Copy-Item "syslog_relay_tray.py" "C:\Users\simon\Desktop\Syslog Relay\syslog_relay_tray.py" -Force
   Copy-Item "start_syslog_relay.bat" "C:\Users\simon\Desktop\Syslog Relay\start_syslog_relay.bat" -Force
   ```

**Why This Matters:**
- The relay runs from the execution folder (Desktop)
- Changes made in the working folder (iCloudDrive) don't automatically apply
- The execution folder must be manually updated for changes to take effect

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
