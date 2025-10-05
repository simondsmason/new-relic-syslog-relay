#!/usr/bin/env python3
import socket
import re
import time
import threading
import sys
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox
import pystray
from PIL import Image, ImageDraw
import os
import psutil
import gc
import platform

# Configuration
LISTEN_PORT = 513
FORWARD_PORT = 514
FORWARD_HOST = '127.0.0.1'

# Hubitat Dual Send Mode - send both converted and original messages
HUBITAT_DUAL_SEND_MODE = True  # Set to True to send both converted and original Hubitat RFC 5424 messages

# Syslog Relay Server Information
# This is the IP address where the syslog relay is running
# Use this IP for configuring Docker containers and devices to send syslog
SYSLOG_RELAY_IP = "192.168.2.70"
SYSLOG_RELAY_PORT = 513

# Version and changelog
VERSION = "1.32"
CHANGELOG = {
    "1.32": "2025-10-05 - Remove HUBITAT_TIMEZONE_OFFSET_FIX as timezone handling moved to Hubitat driver with DST auto-detection",
    "1.31": "2025-10-05 - Add HUBITAT_TIMEZONE_OFFSET_FIX to adjust RFC 5424 timezone offset from -04:00 to -03:00 for Hubitat messages to fix New Relic timestamp display",
    "1.30": "2025-10-05 - Add HUBITAT_DUAL_SEND_MODE to send both converted RFC 3164 and original RFC 5424 messages for proper app_name field parsing in New Relic",
    "1.29": "2025-01-27 - Fix hostname-based matching logic to properly handle external devices with dynamic IPs",
    "1.28": "2025-01-27 - Add hostname-based timezone matching for external devices with dynamic IPs",
    "1.27": "2025-01-27 - Fix timezone issue with UTC timestamps, remove pop-up dialogs, change Status to send health check",
    "1.26": "2025-01-27 - Fix dialog window issues with proper tkinter implementation and improve local logging",
    "1.25": "2025-01-27 - Fix dialog display issues by reverting to messagebox and improve left-click error handling",
    "1.24": "2025-01-27 - Fix tkinter window management issues and add left-click support for tray icon",
    "1.23": "2025-01-27 - Fix startup message system stats collection and improve global variable handling",
    "1.22": "2025-01-27 - Fix system stats error handling to prevent monitoring worker crashes",
    "1.21": "2025-01-27 - Fix global variable declaration syntax error in on_clicked function",
    "1.20": "2025-01-27 - Add restart functionality with restart message and automatic startup message",
    "1.19": "2025-01-27 - Move startup message to main function and add shutdown message when stopping relay",
    "1.18": "2025-01-27 - Add immediate startup messages and improve monitoring worker reliability with startup notification",
    "1.17": "2025-08-29 - Fix syslog-server message generation by resolving monitoring worker race condition and adding error logging",
    "1.16": "2025-08-24 - Add system monitoring that sends performance data to ktranslate only (no local file logging)",
    "1.15": "2025-08-24 - Fix Home Assistant date stripping by making it independent of Docker container processing",
    "1.14": "2025-08-24 - Add configurable IP list for date stripping and extend to Home Assistant messages",
    "1.13": "2025-08-24 - Fix regex patterns in Docker date stripping to prevent hanging on complex messages",
    "1.12": "2025-08-24 - Add Docker container superfluous date stripping for cleaner New Relic display",
    "1.11": "2025-08-24 - Add Docker container hostname transformation for Unraid messages (container[ID]: -> container [ID]:)",
    "1.10": "2025-08-24 - Add comprehensive logging for all incoming and outgoing messages regardless of format",
    "1.09": "2025-08-03 - Use Docker tag field as hostname for cleaner container identification",
    "1.08": "2025-08-03 - Add log file rotation to prevent unlimited log file growth",
    "1.07": "2025-08-03 - Add process ID to message format for better identification",
    "1.06": "2025-08-03 - Add device name to message format for better identification",
    "1.05": "2025-08-03 - Remove dash and space stripping post-processing for cleaner message display",
    "1.04": "2025-08-03 - Fix RFC 5424 parsing to correctly assign hostname and app-name fields",
    "1.03": "2025-08-03 - Add detailed debug logging to log file for RFC 5424 parsing"
}

# Device time zone offsets (hours to add to UTC)
# Internal devices with static IPs - use IP-based matching
DEVICE_OFFSETS = {
    "192.168.2.19": 5,   # HubitatC8Pro-2
    "192.168.2.108": 5,  # HubitatC8Pro
    "192.168.2.162": 5,  # HubitatC7
    "192.168.2.222": 5,  # HubitatC8-2
    "24.60.231.17": 5,   # ShoreC8
    "192.168.2.110": 5,  # Unraid
    "192.168.2.113": 5,  # Home Assistant
}

# Hostname-based timezone offsets for external devices with dynamic IPs
HOSTNAME_OFFSETS = {
    "HubitatC5": 5,      # External Hubitat C5 (dynamic IP)
    # Add more external devices here as needed
}

# IPs that need date stripping (Docker containers, Home Assistant, etc.)
DATE_STRIP_IPS = [
    "192.168.2.110",  # Unraid (Docker containers: frigate, immichFrame, etc.)
    "192.168.2.113",  # Home Assistant (all addons and core)
]

# Global variables for status
relay_running = False
message_count = 0
last_message_time = None

# Log file configuration
DESKTOP_LOG_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "Syslog Relay")
LOG_FILE = os.path.join(DESKTOP_LOG_DIR, 'syslog_relay.log')
MAX_LOG_SIZE = 1 * 1024 * 1024  # 1 MB (reduced from 10 MB for easier log review)
MAX_LOG_FILES = 5  # Keep 5 log files

# System monitoring variables
last_monitoring_time = time.time()
total_messages_processed = 0
last_minute_messages = 0
last_minute_time = time.time()
monitoring_interval = 60  # Check every 60 seconds
start_time = time.time()

def create_tray_icon():
    """Create a simple icon for th
    e system tray"""
    # Create a simple icon (green circle)
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    draw.ellipse([10, 10, width-10, height-10], fill='green', outline='darkgreen', width=2)
    return image

def rotate_log_file():
    """Rotate log file if it exceeds MAX_LOG_SIZE"""
    # Ensure the desktop log directory exists
    os.makedirs(DESKTOP_LOG_DIR, exist_ok=True)
    
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > MAX_LOG_SIZE:
        # Rotate existing backup files
        for i in range(MAX_LOG_FILES - 1, 0, -1):
            old_file = f"{LOG_FILE}.{i}"
            new_file = f"{LOG_FILE}.{i + 1}"
            if os.path.exists(old_file):
                if i == MAX_LOG_FILES - 1:
                    os.remove(old_file)  # Remove oldest
                else:
                    os.rename(old_file, new_file)
        
        # Rotate current log file
        os.rename(LOG_FILE, f"{LOG_FILE}.1")
        print(f"Log file rotated: {LOG_FILE} -> {LOG_FILE}.1")

def log_message_to_file(message_type, source_ip, message, transformed_message=None):
    """Log all messages to the log file for debugging"""
    # Ensure the desktop log directory exists
    os.makedirs(DESKTOP_LOG_DIR, exist_ok=True)
    rotate_log_file()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    with open(LOG_FILE, 'a', encoding='utf-8') as log_file:
        log_file.write(f"\n=== {message_type.upper()} MESSAGE (v{VERSION}) - {timestamp} ===\n")
        log_file.write(f"Source IP: {source_ip}\n")
        log_file.write(f"Raw message: {message.strip()}\n")
        if transformed_message:
            log_file.write(f"Transformed message: {transformed_message.strip()}\n")
        log_file.write(f"==========================================\n")

def is_hubitat_rfc5424_message(message, source_ip):
    """Check if message is a Hubitat RFC 5424 message that should be sent in dual mode"""
    # Check if it's from a Hubitat device
    if source_ip not in DEVICE_OFFSETS:
        return False
    
    # Check if it's RFC 5424 format (contains version "1" after priority)
    rfc5424_pattern = r'<[0-9]+>1\s+\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}[+-]\d{2}:\d{2}'
    return bool(re.search(rfc5424_pattern, message))


def adjust_docker_hostname(message, source_ip):
    """Transform Docker container hostnames for Unraid messages (container[ID]: -> container [ID]:)"""
    # Only process Unraid messages
    if source_ip != "192.168.2.110":
        return message
    
    # Look for pattern: container[ID]: (Docker container format)
    pattern = r'([a-zA-Z0-9_-]+)\[([0-9]+)\]:'
    match = re.search(pattern, message)
    
    if match:
        container_name = match.group(1)
        container_id = match.group(2)
        # Replace container[ID]: with container [ID]:
        return re.sub(pattern, f'{container_name} [{container_id}]:', message)
    
    return message

def strip_docker_dates(message, source_ip):
    """Strip superfluous date information from Docker container and Home Assistant messages"""
    # Only process messages from configured IPs
    if source_ip not in DATE_STRIP_IPS:
        return message
    
    try:
        # Process Docker container dates (Unraid)
        if source_ip == "192.168.2.110":
            # Look for Docker container pattern to identify these messages
            container_pattern = r'([a-zA-Z0-9_-]+)\s*\[([0-9]+)\]:'
            if re.search(container_pattern, message):
                # Pattern 1: Frigate ISO format with microseconds (2025-08-24 08:54:23.339023614)
                # Use more specific pattern to avoid catastrophic backtracking
                message = re.sub(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+', '', message)
                
                # Pattern 1b: Remove bracketed timestamps that might follow ([2025-08-24 08:54:23])
                message = re.sub(r'\s*\[\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\]\s*', ' ', message)
                
                # Pattern 2: ImmichFrame short date format (25-08-24 08:54:24)
                message = re.sub(r'\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+', '', message)
        
        # Process Home Assistant dates (independent check)
        if source_ip == "192.168.2.113" and "homeassistant" in message:
            # Pattern 1: Home Assistant ISO format with milliseconds (2025-08-24 17:56:26.257)
            message = re.sub(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+', '', message)
            
            # Pattern 2: Home Assistant ISO format with comma-separated milliseconds (2025-08-24 17:57:52,121)
            message = re.sub(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d+', '', message)
            
            # Pattern 3: Home Assistant ISO format with colon separator (2025-08-24 17:58:37:)
            message = re.sub(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}:', '', message)
        
        # Clean up any double spaces that might result
        message = re.sub(r'\s+', ' ', message)
        
        return message
    except Exception as e:
        # If regex processing fails, return original message
        print(f"Warning: Date stripping failed for message: {e}")
        return message

def adjust_timestamp(message, source_ip):
    """Adjust timestamp in syslog message based on source IP or hostname"""
    global message_count, last_message_time
    
    # First, check if IP is in DEVICE_OFFSETS (standard IP-based matching)
    if source_ip in DEVICE_OFFSETS:
        offset_hours = DEVICE_OFFSETS[source_ip]
        print(f"Using IP-based offset for {source_ip}: {offset_hours} hours")
    else:
        # IP not found in DEVICE_OFFSETS, try hostname-based matching for external devices
        # Extract hostname from the message for external devices with dynamic IPs
        # Look for RFC 5424 format: <priority>1 timestamp hostname app-name ...
        rfc5424_pattern = r'<[0-9]+>1\s+\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}[+-]\d{2}:\d{2}\s+([^\s]+)'
        match = re.search(rfc5424_pattern, message)
        if match:
            hostname = match.group(1)
            if hostname in HOSTNAME_OFFSETS:
                offset_hours = HOSTNAME_OFFSETS[hostname]
                print(f"Using hostname-based offset for {hostname} (IP: {source_ip}): {offset_hours} hours")
            else:
                # No hostname match found, return original message unchanged
                print(f"No hostname match for {hostname} (IP: {source_ip}), no processing needed")
                return message
        else:
            # Could not extract hostname, return original message unchanged
            print(f"Could not extract hostname from message (IP: {source_ip}), no processing needed")
            return message
    
    # Try ISO 8601 format first (Hubitat format): <priority>1 YYYY-MM-DDTHH:MM:SS.mmm±HH:MM
    iso_pattern = r'(<[0-9]+>1\s+)(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}[+-]\d{2}:\d{2})'
    iso_match = re.search(iso_pattern, message)
    
    if iso_match:
        priority_part = iso_match.group(1)
        timestamp = iso_match.group(2)
        
        try:
            # Parse ISO timestamp
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            # Add the offset
            adjusted_dt = dt + timedelta(hours=offset_hours)
            
            # Format to traditional syslog format (Month Day HH:MM:SS)
            adjusted_timestamp = adjusted_dt.strftime("%b %d %H:%M:%S")
            
            # Convert entire RFC 5424 format to RFC 3164 format
            # Extract components from the message
            # Format: <priority>1 timestamp hostname app-name process-id message-id structured-data message
            parts = message.split(' ', 7)  # Split into 8 parts
            if len(parts) >= 8:
                priority = parts[0]  # <14>1
                # Remove the "1" from priority
                priority = priority.replace('1', '')
                hostname = parts[2]  # HubitatC8Pro (actual hostname)
                app_name = parts[3]  # Watchdog.-.Motion.Sensors.-.Virtual.Switch (app name)
                message_content = parts[7]  # The actual message
                
                # Debug: Print the parsed components
                print(f"DEBUG - Parsed components:")
                print(f"  Priority: {priority}")
                print(f"  Hostname: {hostname}")
                print(f"  App name: {app_name}")
                print(f"  Message content: {message_content}")
                
                # Rotate log file if needed
                rotate_log_file()
                
                # Write debug info to log file
                with open(LOG_FILE, 'a', encoding='utf-8') as log_file:
                    log_file.write(f"\n=== RFC 5424 PARSING DEBUG (v{VERSION}) ===\n")
                    log_file.write(f"Raw message: {message.strip()}\n")
                    log_file.write(f"Split into {len(parts)} parts:\n")
                    for i, part in enumerate(parts):
                        log_file.write(f"  parts[{i}]: '{part}'\n")
                    log_file.write(f"Assigned fields:\n")
                    log_file.write(f"  Priority: '{priority}' (from parts[0])\n")
                    log_file.write(f"  Hostname: '{hostname}' (from parts[2])\n")
                    log_file.write(f"  App name: '{app_name}' (from parts[3])\n")
                    log_file.write(f"  Message content: '{message_content}' (from parts[7])\n")
                    log_file.write(f"==========================================\n")
                
                # Check if this is a Docker message by looking for container ID pattern in hostname
                # Docker container IDs are 12-character hex strings like "5183c0a146c0"
                docker_tag = None
                if re.match(r'^[a-f0-9]{12}$', hostname):
                    # This is likely a Docker container ID
                    # Map container IDs to friendly names
                    docker_container_mapping = {
                        '5183c0a146c0': 'immichFrame-All',  # Add more mappings as needed
                    }
                    if hostname in docker_container_mapping:
                        docker_tag = docker_container_mapping[hostname]
                        print(f"Detected Docker container {hostname}, using tag: {docker_tag}")
                    else:
                        print(f"Detected Docker container {hostname}, but no mapping found")
                
                # Clean up app_name by removing HTML tags
                app_name_clean = re.sub(r'<[^>]+>', '', app_name)
                
                # Further clean app_name to remove special characters that might confuse ktranslate
                app_name_clean = re.sub(r'[^\w\-\.]', '_', app_name_clean)
                
                # Use Docker tag as hostname if available, otherwise use original hostname
                final_hostname = docker_tag if docker_tag else hostname
                
                # Create RFC 3164 format: <priority>timestamp hostname app-name: app-name (process-id) - message
                # Use a format that ktranslate can properly parse
                # For Docker messages, use the tag as hostname for cleaner identification
                # For other devices, keep the original hostname (HubitatC8Pro, HubitatC7, etc.)
                adjusted_message = f"{priority}{adjusted_timestamp} {final_hostname} {app_name_clean}: {app_name_clean} ({parts[4]}) - {message_content}"
            else:
                # Fallback to simple timestamp replacement if parsing fails
                adjusted_message = re.sub(iso_pattern, f"{priority_part}{adjusted_timestamp}", message)
            
            # Update counters
            message_count += 1
            last_message_time = datetime.now()
            
            print(f"Converted RFC 5424 to RFC 3164 from {source_ip} (+{offset_hours}h): {timestamp} -> {adjusted_timestamp}")
            return adjusted_message
            
        except Exception as e:
            print(f"Error adjusting ISO timestamp: {e}")
            return message
    
    # Try traditional syslog format: <priority>Month Day HH:MM:SS
    traditional_pattern = r'(<[0-9]+>)([A-Za-z]{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})'
    traditional_match = re.search(traditional_pattern, message)
    
    if traditional_match:
        priority = traditional_match.group(1)
        timestamp = traditional_match.group(2)
        
        try:
            # Parse the timestamp (assuming current year)
            current_year = datetime.now().year
            timestamp_str = f"{current_year} {timestamp}"
            dt = datetime.strptime(timestamp_str, "%Y %b %d %H:%M:%S")
            
            # Add the offset
            adjusted_dt = dt + timedelta(hours=offset_hours)
            
            # Format back to syslog format
            adjusted_timestamp = adjusted_dt.strftime("%b %d %H:%M:%S")
            
            # Replace in message
            adjusted_message = re.sub(traditional_pattern, f"{priority}{adjusted_timestamp}", message)
            
            # Update counters
            message_count += 1
            last_message_time = datetime.now()
            
            print(f"Adjusted traditional timestamp from {source_ip} (+{offset_hours}h): {timestamp} -> {adjusted_timestamp}")
            return adjusted_message
            
        except Exception as e:
            print(f"Error adjusting traditional timestamp: {e}")
            return message
    
    return message

def relay_worker():
    """Main relay function"""
    global relay_running
    
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', LISTEN_PORT))
    
    # Create forwarding socket
    forward_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    print(f"Syslog relay v{VERSION} started. Listening on port {LISTEN_PORT}, forwarding to {FORWARD_HOST}:{FORWARD_PORT}")
    print(f"Device offsets: {DEVICE_OFFSETS}")
    
    relay_running = True
    
    try:
        while relay_running:
            # Receive message with timeout
            sock.settimeout(1.0)
            try:
                data, addr = sock.recvfrom(1024)
                message = data.decode('utf-8', errors='ignore')
                source_ip = addr[0]
                
                print(f"=== INCOMING MESSAGE (v{VERSION}) ===")
                print(f"Source IP: {source_ip}")
                print(f"Raw message: {message.strip()}")
                
                # Log incoming message
                log_message_to_file("incoming", source_ip, message)
                
                # Adjust timestamp if needed
                adjusted_message = adjust_timestamp(message, source_ip)
                
                # Transform Docker hostname if needed
                transformed_message = adjust_docker_hostname(adjusted_message, source_ip)
                
                # Strip Docker dates if needed
                final_message = strip_docker_dates(transformed_message, source_ip)
                
                print(f"=== OUTGOING MESSAGE (v{VERSION}) ===")
                print(f"Transformed message: {final_message}")
                print(f"Destination: {FORWARD_HOST}:{FORWARD_PORT}")
                print(f"========================")
                
                # Forward to ktranslate
                forward_sock.sendto(final_message.encode('utf-8'), (FORWARD_HOST, FORWARD_PORT))
                
                # NEW: Send original RFC 5424 message for Hubitat devices only (if enabled)
                if HUBITAT_DUAL_SEND_MODE and is_hubitat_rfc5424_message(message, source_ip):
                    # Only send original if it's a Hubitat RFC 5424 message
                    forward_sock.sendto(message.encode('utf-8'), (FORWARD_HOST, FORWARD_PORT))
                    print(f"=== HUBITAT DUAL SEND: ORIGINAL RFC 5424 (v{VERSION}) ===")
                    print(f"Original message: {message.strip()}")
                    print(f"Destination: {FORWARD_HOST}:{FORWARD_PORT}")
                    print(f"========================")
                
                # Log outgoing message
                log_message_to_file("outgoing", source_ip, message, final_message)
                
                # NEW: Log Hubitat dual send if enabled
                if HUBITAT_DUAL_SEND_MODE and is_hubitat_rfc5424_message(message, source_ip):
                    log_message_to_file("hubitat_dual_send_original", source_ip, message)
                
            except socket.timeout:
                # No message received, continue
                continue
            except Exception as e:
                print(f"Error processing message: {e}")
                
    except Exception as e:
        print(f"Relay error: {e}")
    finally:
        sock.close()
        forward_sock.close()
        relay_running = False

def get_system_stats():
    """Collect comprehensive system statistics"""
    try:
        # Get system memory info
        memory = psutil.virtual_memory()
        
        # Get current process info
        process = psutil.Process()
        process_memory = process.memory_info()
        process_cpu = process.cpu_percent()
        
        # Get CPU usage
        cpu_percent = psutil.cpu_percent()
        
        # Get disk usage for C: drive
        disk = psutil.disk_usage('C:\\')
        
        # Get network stats
        network = psutil.net_io_counters()
        
        # Get uptime - handle case where start_time might not be initialized
        try:
            uptime = time.time() - start_time
        except NameError:
            uptime = 0
        
        # Calculate message rates - handle case where global variables might not be initialized
        try:
            current_time = time.time()
            if current_time - last_minute_time >= 60:
                messages_per_minute = last_minute_messages
                last_minute_messages = 0
                last_minute_time = current_time
            else:
                messages_per_minute = last_minute_messages
        except NameError:
            messages_per_minute = 0
        
        # Get active threads
        active_threads = threading.active_count()
        
        # Get garbage collection stats
        gc_stats = gc.get_stats()
        
        # Handle case where global variables might not be initialized
        try:
            total_messages = total_messages_processed
        except NameError:
            total_messages = 0
        
        try:
            relay_status = relay_running
        except NameError:
            relay_status = False
        
        stats = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'version': VERSION,
            'uptime_seconds': int(uptime),
            'uptime_formatted': f"{int(uptime//3600)}h {int((uptime%3600)//60)}m {int(uptime%60)}s",
            'memory_total_gb': round(memory.total / (1024**3), 2),
            'memory_used_gb': round(memory.used / (1024**3), 2),
            'memory_available_gb': round(memory.available / (1024**3), 2),
            'memory_percent': memory.percent,
            'process_memory_mb': round(process_memory.rss / (1024**2), 2),
            'cpu_percent': cpu_percent,
            'process_cpu_percent': process_cpu,
            'disk_total_gb': round(disk.total / (1024**3), 2),
            'disk_used_gb': round(disk.used / (1024**3), 2),
            'disk_free_gb': round(disk.free / (1024**3), 2),
            'disk_percent': round((disk.used / disk.total) * 100, 2),
            'network_bytes_sent_mb': round(network.bytes_sent / (1024**2), 2),
            'network_bytes_recv_mb': round(network.bytes_recv / (1024**2), 2),
            'total_messages': total_messages,
            'messages_per_minute': messages_per_minute,
            'active_threads': active_threads,
            'relay_running': relay_status,
            'gc_collections': len(gc_stats),
            'gc_objects_collected': sum(stat['collections'] for stat in gc_stats),
            'platform': platform.platform(),
            'python_version': platform.python_version(),
        }
        return stats
    except Exception as e:
        return {'error': f"Failed to collect system stats: {e}"}

def send_startup_message(forward_sock):
    """Send startup message to ktranslate via syslog"""
    try:
        priority = "<134>"  # Info level
        timestamp = datetime.utcnow().strftime("%b %d %H:%M:%S")
        hostname = "syslog-relay"
        app_name = "relay-startup"
        
        # Get basic system info directly without using get_system_stats()
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent()
            memory_info = f"{memory.percent}%({round(memory.used / (1024**3), 2)}GB/{round(memory.total / (1024**3), 2)}GB)"
            cpu_info = f"{cpu_percent}%"
        except Exception as e:
            print(f"Error getting basic system stats: {e}")
            memory_info = "Unknown"
            cpu_info = "Unknown"
        
        message_parts = [
            f"Version:{VERSION}",
            f"Platform:{platform.system()} {platform.release()}",
            f"Python:{platform.python_version()}",
            f"Startup:{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Memory:{memory_info}",
            f"CPU:{cpu_info}",
            f"Status:Starting"
        ]
        
        syslog_message = f"{priority}{timestamp} {hostname} {app_name}: {' | '.join(message_parts)}"
        forward_sock.sendto(syslog_message.encode('utf-8'), (FORWARD_HOST, FORWARD_PORT))
        print(f"Startup message sent to ktranslate: {syslog_message}")
        
        # Also log to file for debugging
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as log_file:
                log_file.write(f"\n=== STARTUP MESSAGE SENT (v{VERSION}) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                log_file.write(f"Message: {syslog_message}\n")
                log_file.write(f"==========================================\n")
        except:
            pass
            
    except Exception as e:
        error_msg = f"Error sending startup message to ktranslate: {e}"
        print(error_msg)
        # Log error to file
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as log_file:
                log_file.write(f"\n=== STARTUP MESSAGE ERROR (v{VERSION}) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                log_file.write(f"{error_msg}\n")
                log_file.write(f"==========================================\n")
        except:
            pass

def send_shutdown_message(forward_sock):
    """Send shutdown message to ktranslate via syslog"""
    try:
        priority = "<134>"  # Info level
        timestamp = datetime.utcnow().strftime("%b %d %H:%M:%S")
        hostname = "syslog-relay"
        app_name = "relay-shutdown"
        
        # Get basic system info for shutdown message
        stats = get_system_stats()
        
        # Check if stats collection failed
        if 'error' in stats:
            # Use fallback values if stats collection failed
            message_parts = [
                f"Version:{VERSION}",
                f"Platform:{platform.system()} {platform.release()}",
                f"Python:{platform.python_version()}",
                f"Shutdown:{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Memory:Unknown",
                f"CPU:Unknown",
                f"Messages:Unknown",
                f"Status:Stopping"
            ]
        else:
            message_parts = [
                f"Version:{VERSION}",
                f"Platform:{platform.system()} {platform.release()}",
                f"Python:{platform.python_version()}",
                f"Shutdown:{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Memory:{stats.get('memory_percent', 'Unknown')}%({stats.get('memory_used_gb', 'Unknown')}GB/{stats.get('memory_total_gb', 'Unknown')}GB)",
                f"CPU:{stats.get('cpu_percent', 'Unknown')}%",
                f"Messages:{stats.get('total_messages', 'Unknown')}",
                f"Status:Stopping"
            ]
        
        syslog_message = f"{priority}{timestamp} {hostname} {app_name}: {' | '.join(message_parts)}"
        forward_sock.sendto(syslog_message.encode('utf-8'), (FORWARD_HOST, FORWARD_PORT))
        print(f"Shutdown message sent to ktranslate: {syslog_message}")
        
        # Also log to file for debugging
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as log_file:
                log_file.write(f"\n=== SHUTDOWN MESSAGE SENT (v{VERSION}) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                log_file.write(f"Message: {syslog_message}\n")
                log_file.write(f"==========================================\n")
        except:
            pass
            
    except Exception as e:
        error_msg = f"Error sending shutdown message to ktranslate: {e}"
        print(error_msg)
        # Log error to file
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as log_file:
                log_file.write(f"\n=== SHUTDOWN MESSAGE ERROR (v{VERSION}) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                log_file.write(f"{error_msg}\n")
                log_file.write(f"==========================================\n")
        except:
            pass

def send_restart_message(forward_sock):
    """Send restart message to ktranslate via syslog"""
    try:
        priority = "<134>"  # Info level
        timestamp = datetime.utcnow().strftime("%b %d %H:%M:%S")
        hostname = "syslog-relay"
        app_name = "relay-restart"
        
        # Get basic system info for restart message
        stats = get_system_stats()
        
        # Check if stats collection failed
        if 'error' in stats:
            # Use fallback values if stats collection failed
            message_parts = [
                f"Version:{VERSION}",
                f"Platform:{platform.system()} {platform.release()}",
                f"Python:{platform.python_version()}",
                f"Restart:{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Memory:Unknown",
                f"CPU:Unknown",
                f"Messages:Unknown",
                f"Status:Restarting"
            ]
        else:
            message_parts = [
                f"Version:{VERSION}",
                f"Platform:{platform.system()} {platform.release()}",
                f"Python:{platform.python_version()}",
                f"Restart:{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Memory:{stats.get('memory_percent', 'Unknown')}%({stats.get('memory_used_gb', 'Unknown')}GB/{stats.get('memory_total_gb', 'Unknown')}GB)",
                f"CPU:{stats.get('cpu_percent', 'Unknown')}%",
                f"Messages:{stats.get('total_messages', 'Unknown')}",
                f"Status:Restarting"
            ]
        
        syslog_message = f"{priority}{timestamp} {hostname} {app_name}: {' | '.join(message_parts)}"
        forward_sock.sendto(syslog_message.encode('utf-8'), (FORWARD_HOST, FORWARD_PORT))
        print(f"Restart message sent to ktranslate: {syslog_message}")
        
        # Also log to file for debugging
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as log_file:
                log_file.write(f"\n=== RESTART MESSAGE SENT (v{VERSION}) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                log_file.write(f"Message: {syslog_message}\n")
                log_file.write(f"==========================================\n")
        except:
            pass
            
    except Exception as e:
        error_msg = f"Error sending restart message to ktranslate: {e}"
        print(error_msg)
        # Log error to file
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as log_file:
                log_file.write(f"\n=== RESTART MESSAGE ERROR (v{VERSION}) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                log_file.write(f"{error_msg}\n")
                log_file.write(f"==========================================\n")
        except:
            pass

def send_system_stats_to_ktranslate(stats, forward_sock):
    """Send system statistics to ktranslate via syslog"""
    try:
        priority = "<134>"  # Info level
        timestamp = datetime.utcnow().strftime("%b %d %H:%M:%S")
        hostname = "syslog-relay"
        app_name = "system-monitor"
        
        # Check if stats collection failed
        if 'error' in stats:
            # Use fallback values if stats collection failed
            message_parts = [
                f"Uptime:Unknown",
                f"Memory:Unknown",
                f"Process:Unknown",
                f"CPU:Unknown",
                f"Disk:Unknown",
                f"Messages:Unknown",
                f"Threads:Unknown",
                f"Relay:{'Running' if relay_running else 'Stopped'}"
            ]
        else:
            message_parts = [
                f"Uptime:{stats.get('uptime_formatted', 'Unknown')}",
                f"Memory:{stats.get('memory_percent', 'Unknown')}%({stats.get('memory_used_gb', 'Unknown')}GB/{stats.get('memory_total_gb', 'Unknown')}GB)",
                f"Process:{stats.get('process_memory_mb', 'Unknown')}MB",
                f"CPU:{stats.get('cpu_percent', 'Unknown')}%",
                f"Disk:{stats.get('disk_percent', 'Unknown')}%({stats.get('disk_used_gb', 'Unknown')}GB/{stats.get('disk_total_gb', 'Unknown')}GB)",
                f"Messages:{stats.get('total_messages', 'Unknown')}({stats.get('messages_per_minute', 'Unknown')}/min)",
                f"Threads:{stats.get('active_threads', 'Unknown')}",
                f"Relay:{'Running' if stats.get('relay_running', relay_running) else 'Stopped'}"
            ]
        
        syslog_message = f"{priority}{timestamp} {hostname} {app_name}: {' | '.join(message_parts)}"
        forward_sock.sendto(syslog_message.encode('utf-8'), (FORWARD_HOST, FORWARD_PORT))
        print(f"System stats sent to ktranslate: {syslog_message}")
        
        # Also log to file for debugging
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as log_file:
                log_file.write(f"\n=== SYSTEM STATS SENT (v{VERSION}) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                log_file.write(f"Message: {syslog_message}\n")
                log_file.write(f"==========================================\n")
        except:
            pass
            
    except Exception as e:
        error_msg = f"Error sending system stats to ktranslate: {e}"
        print(error_msg)
        # Log error to file
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as log_file:
                log_file.write(f"\n=== SYSTEM STATS ERROR (v{VERSION}) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                log_file.write(f"{error_msg}\n")
                log_file.write(f"==========================================\n")
        except:
            pass

def monitoring_worker():
    """Background worker for periodic system monitoring"""
    global last_monitoring_time, total_messages_processed, last_minute_messages
    
    print(f"Monitoring worker starting (v{VERSION})")
    
    try:
        monitor_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print("Monitoring socket created successfully")
    except Exception as e:
        print(f"Failed to create monitoring socket: {e}")
        # Log to file if possible
        try:
            os.makedirs(DESKTOP_LOG_DIR, exist_ok=True)
            with open(LOG_FILE, 'a', encoding='utf-8') as log_file:
                log_file.write(f"\n=== MONITORING WORKER ERROR (v{VERSION}) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                log_file.write(f"Failed to create monitoring socket: {e}\n")
                log_file.write(f"==========================================\n")
        except:
            pass
        return
    
    # Wait for relay to be running before starting monitoring loop
    wait_count = 0
    while not relay_running and wait_count < 30:  # Wait up to 30 seconds
        time.sleep(1)
        wait_count += 1
    
    if not relay_running:
        print("Monitoring worker exiting: relay not running after 30 seconds")
        monitor_sock.close()
        return
    
    print(f"Monitoring worker started successfully, relay_running={relay_running}")
    
    # Send first system stats message immediately
    print("Sending initial system stats...")
    stats = get_system_stats()
    send_system_stats_to_ktranslate(stats, monitor_sock)
    last_monitoring_time = time.time()  # Reset timer for next 60-second interval
    
    while relay_running:
        try:
            current_time = time.time()
            
            # Check if it's time for monitoring
            if current_time - last_monitoring_time >= monitoring_interval:
                last_monitoring_time = current_time
                stats = get_system_stats()
                send_system_stats_to_ktranslate(stats, monitor_sock)
                print(f"System monitoring completed at {stats['timestamp']}")
            
            # Update message counters
            if message_count > total_messages_processed:
                last_minute_messages += (message_count - total_messages_processed)
                total_messages_processed = message_count
            
            time.sleep(10)  # Check every 10 seconds
            
        except Exception as e:
            error_msg = f"Error in monitoring worker: {e}"
            print(error_msg)
            # Log error to file
            try:
                with open(LOG_FILE, 'a', encoding='utf-8') as log_file:
                    log_file.write(f"\n=== MONITORING WORKER ERROR (v{VERSION}) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                    log_file.write(f"{error_msg}\n")
                    log_file.write(f"==========================================\n")
            except:
                pass
            time.sleep(30)  # Wait longer on error
    
    print("Monitoring worker shutting down")
    monitor_sock.close()

def send_health_check_message(forward_sock):
    """Send health check message to ktranslate via syslog"""
    try:
        priority = "<134>"  # Info level
        timestamp = datetime.utcnow().strftime("%b %d %H:%M:%S")
        hostname = "syslog-relay"
        app_name = "relay-health-check"
        
        # Get current system stats
        stats = get_system_stats()
        
        # Check if stats collection failed
        if 'error' in stats:
            # Use fallback values if stats collection failed
            message_parts = [
                f"Version:{VERSION}",
                f"Platform:{platform.system()} {platform.release()}",
                f"Python:{platform.python_version()}",
                f"HealthCheck:{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Memory:Unknown",
                f"CPU:Unknown",
                f"Messages:Unknown",
                f"Status:Manual Check"
            ]
        else:
            message_parts = [
                f"Version:{VERSION}",
                f"Platform:{platform.system()} {platform.release()}",
                f"Python:{platform.python_version()}",
                f"HealthCheck:{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Memory:{stats.get('memory_percent', 'Unknown')}%({stats.get('memory_used_gb', 'Unknown')}GB/{stats.get('memory_total_gb', 'Unknown')}GB)",
                f"CPU:{stats.get('cpu_percent', 'Unknown')}%",
                f"Messages:{stats.get('total_messages', 'Unknown')}",
                f"Status:Manual Check"
            ]
        
        syslog_message = f"{priority}{timestamp} {hostname} {app_name}: {' | '.join(message_parts)}"
        forward_sock.sendto(syslog_message.encode('utf-8'), (FORWARD_HOST, FORWARD_PORT))
        print(f"Health check message sent to ktranslate: {syslog_message}")
        
        # Also log to file for debugging
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as log_file:
                log_file.write(f"\n=== HEALTH CHECK MESSAGE SENT (v{VERSION}) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                log_file.write(f"Message: {syslog_message}\n")
                log_file.write(f"==========================================\n")
        except:
            pass
            
    except Exception as e:
        error_msg = f"Error sending health check message to ktranslate: {e}"
        print(error_msg)
        # Log error to file
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as log_file:
                log_file.write(f"\n=== HEALTH CHECK MESSAGE ERROR (v{VERSION}) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                log_file.write(f"{error_msg}\n")
                log_file.write(f"==========================================\n")
        except:
            pass

def on_clicked(icon, item):
    """Handle tray icon clicks"""
    global relay_running
    
    if str(item) == f"Status (v{VERSION})":
        # Send health check message
        try:
            health_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            send_health_check_message(health_sock)
            health_sock.close()
        except Exception as e:
            print(f"Error sending health check message: {e}")
    elif str(item) == "Stop":
        relay_running = False
        
        # Send shutdown message before stopping
        try:
            shutdown_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            send_shutdown_message(shutdown_sock)
            shutdown_sock.close()
        except Exception as e:
            print(f"Error sending shutdown message: {e}")
        
        icon.stop()
    elif str(item) == "Restart":
        # Send restart message
        try:
            restart_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            send_restart_message(restart_sock)
            restart_sock.close()
        except Exception as e:
            print(f"Error sending restart message: {e}")
        
        # Stop the current relay
        relay_running = False
        
        # Wait a moment for cleanup
        time.sleep(1)
        
        # Restart the relay
        relay_running = True
        
        # Start relay in background thread
        relay_thread = threading.Thread(target=relay_worker, daemon=True)
        relay_thread.start()
        
        # Give relay worker time to set relay_running = True before starting monitoring
        time.sleep(2)
        
        # Send startup message
        try:
            startup_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            send_startup_message(startup_sock)
            startup_sock.close()
        except Exception as e:
            print(f"Error sending startup message: {e}")
        
        # Start monitoring in background thread
        monitoring_thread = threading.Thread(target=monitoring_worker, daemon=True)
        monitoring_thread.start()

def main():
    # Start relay in background thread
    relay_thread = threading.Thread(target=relay_worker, daemon=True)
    relay_thread.start()
    
    # Give relay worker time to set relay_running = True before starting monitoring
    time.sleep(2)
    
    # Send startup message immediately
    try:
        startup_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        send_startup_message(startup_sock)
        startup_sock.close()
    except Exception as e:
        print(f"Error sending startup message: {e}")
    
    # Start monitoring in background thread
    monitoring_thread = threading.Thread(target=monitoring_worker, daemon=True)
    monitoring_thread.start()
    
    # Create tray icon
    icon_image = create_tray_icon()
    
    # Create menu for right-click
    menu = pystray.Menu(
        pystray.MenuItem(f"Status (v{VERSION})", on_clicked),
        pystray.MenuItem("Stop", on_clicked),
        pystray.MenuItem("Restart", on_clicked)
    )
    
    # Create and run tray icon
    icon = pystray.Icon("syslog_relay", icon_image, f"Syslog Relay v{VERSION}", menu)
    
    print(f"Syslog relay v{VERSION} started with tray icon. Right-click the tray icon for options.")
    
    try:
        icon.run()
    except KeyboardInterrupt:
        relay_running = False
        icon.stop()

if __name__ == "__main__":
    main() 