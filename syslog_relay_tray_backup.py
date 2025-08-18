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

# Configuration
LISTEN_PORT = 513
FORWARD_PORT = 514
FORWARD_HOST = '127.0.0.1'

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
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_LOG_FILES = 5  # Keep 5 log files

def create_tray_icon():
    """Create a simple icon for the system tray"""
    # Create a simple icon (green circle)
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    draw.ellipse([10, 10, width-10, height-10], fill='green', outline='darkgreen', width=2)
    return image

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
            
            # Replace in message - convert from ISO format to traditional format
            adjusted_message = re.sub(iso_pattern, f"{priority_part}{adjusted_timestamp}", message)
            
            # Update counters
            message_count += 1
            last_message_time = datetime.now()
            
            print(f"Adjusted ISO timestamp from {source_ip} (+{offset_hours}h): {timestamp} -> {adjusted_timestamp} (traditional format)")
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
    
    print(f"Syslog relay started. Listening on port {LISTEN_PORT}, forwarding to {FORWARD_HOST}:{FORWARD_PORT}")
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
                
                print(f"Received from {source_ip}: {message.strip()}")
                
                # Adjust timestamp if needed
                adjusted_message = adjust_timestamp(message, source_ip)
                
                # Forward to ktranslate
                forward_sock.sendto(adjusted_message.encode('utf-8'), (FORWARD_HOST, FORWARD_PORT))
                print(f"Forwarded to {FORWARD_HOST}:{FORWARD_PORT}")
                
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
        return "Syslog Relay: Stopped"
    
    status = f"Syslog Relay: Running\nMessages: {message_count}"
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
    icon = pystray.Icon("syslog_relay", icon_image, "Syslog Relay", menu)
    
    print("Syslog relay started with tray icon. Right-click the tray icon for options.")
    
    try:
        icon.run()
    except KeyboardInterrupt:
        relay_running = False
        icon.stop()

if __name__ == "__main__":
    main() 