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

# Configuration
LISTEN_PORT = 513
FORWARD_PORT = 514
FORWARD_HOST = '127.0.0.1'

# Version and changelog
VERSION = "1.09"
CHANGELOG = {
    "1.09": "2025-08-03 - Use Docker tag field as hostname for cleaner container identification",
    "1.08": "2025-08-03 - Add log file rotation to prevent unlimited log file growth",
    "1.07": "2025-08-03 - Add process ID to message format for better identification",
    "1.06": "2025-08-03 - Add device name to message format for better identification",
    "1.05": "2025-08-03 - Remove dash and space stripping post-processing for cleaner message display",
    "1.04": "2025-08-03 - Fix RFC 5424 parsing to correctly assign hostname and app-name fields",
    "1.03": "2025-08-03 - Add detailed debug logging to log file for RFC 5424 parsing",
    "1.02": "2025-08-03 - Preserve original hostname in Hubitat RFC 5424 to RFC 3164 conversion",
    "1.01": "2025-08-03 - Strip leading dash and space from Hubitat messages for cleaner New Relic display",
    "1.00": "2025-07-26 - Initial version with detailed incoming/outgoing message logging"
}

# Device IPs and their timezone offsets (in hours)
DEVICE_OFFSETS = {
    '192.168.2.110': 5,  # Unraid: +5 hours
    '192.168.2.108': 5,  # Hubitat: +5 hours (updated to match others)
    '192.168.2.162': 5,  # Hubitat: +5 hours (updated to match others)
    '192.168.2.19': 5,   # Hubitat: +5 hours (updated to match others)
    '192.168.2.222': 5,  # Hubitat: +5 hours (updated to match others)
    '192.168.2.113': 5,  # Home Assistant: +5 hours
}

# Global variables for status
relay_running = False
message_count = 0
last_message_time = None

# Log file configuration
LOG_FILE = 'syslog_relay.log'
MAX_LOG_SIZE = 1 * 1024 * 1024  # 1 MB (reduced from 10 MB for easier log review)
MAX_LOG_FILES = 5  # Keep 5 log files

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

def adjust_timestamp(message, source_ip):
    """Adjust timestamp in syslog message based on source IP"""
    global message_count, last_message_time
    
    if source_ip not in DEVICE_OFFSETS:
        return message
    
    offset_hours = DEVICE_OFFSETS[source_ip]
    
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
                
                # Adjust timestamp if needed
                adjusted_message = adjust_timestamp(message, source_ip)
                

                
                print(f"=== OUTGOING MESSAGE (v{VERSION}) ===")
                print(f"Transformed message: {adjusted_message}")
                print(f"Destination: {FORWARD_HOST}:{FORWARD_PORT}")
                print(f"========================")
                
                # Forward to ktranslate
                forward_sock.sendto(adjusted_message.encode('utf-8'), (FORWARD_HOST, FORWARD_PORT))
                
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

def get_status_text():
    """Get status text for tray icon"""
    if not relay_running:
        return f"Syslog Relay v{VERSION}: Stopped"
    
    status = f"Syslog Relay v{VERSION}: Running\nMessages: {message_count}"
    if last_message_time:
        status += f"\nLast: {last_message_time.strftime('%H:%M:%S')}"
    return status

def on_clicked(icon, item):
    """Handle tray icon clicks"""
    if str(item) == "Status":
        messagebox.showinfo("Syslog Relay Status", get_status_text())
    elif str(item) == "Stop":
        global relay_running
        relay_running = False
        icon.stop()
    elif str(item) == "Restart":
        # Restart functionality could be added here
        messagebox.showinfo("Restart", "Please restart the application to restart the relay")

def main():
    # Start relay in background thread
    relay_thread = threading.Thread(target=relay_worker, daemon=True)
    relay_thread.start()
    
    # Create tray icon
    icon_image = create_tray_icon()
    
    # Create menu
    menu = pystray.Menu(
        pystray.MenuItem("Status", on_clicked),
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