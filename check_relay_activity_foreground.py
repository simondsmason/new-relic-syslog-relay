#!/usr/bin/env python3
import socket
import time
import threading
from datetime import datetime

def monitor_port_513():
    """Monitor port 513 - incoming messages to relay"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', 513))
    
    print(f"Monitoring port 513 (incoming to relay)...")
    
    try:
        while True:
            sock.settimeout(5.0)
            try:
                data, addr = sock.recvfrom(1024)
                message = data.decode('utf-8', errors='ignore')
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                print(f"\n[{timestamp}] PORT 513 - INCOMING from {addr[0]}:{addr[1]}")
                print(f"Message: {message.strip()}")
                
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Port 513 Error: {e}")
                
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()

def monitor_port_514():
    """Monitor port 514 - outgoing messages from relay to ktranslate"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', 514))
    
    print(f"Monitoring port 514 (outgoing from relay)...")
    
    try:
        while True:
            sock.settimeout(5.0)
            try:
                data, addr = sock.recvfrom(1024)
                message = data.decode('utf-8', errors='ignore')
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                # Clean up the message by stripping leading dashes and spaces
                cleaned_message = message.strip()
                if cleaned_message.startswith('- '):
                    cleaned_message = cleaned_message[2:]  # Remove "- " prefix
                elif cleaned_message.startswith('-'):
                    cleaned_message = cleaned_message[1:]  # Remove "-" prefix
                cleaned_message = cleaned_message.strip()  # Remove any remaining leading/trailing spaces
                
                print(f"\n[{timestamp}] PORT 514 - OUTGOING from {addr[0]}:{addr[1]}")
                print(f"Message: {cleaned_message}")
                
                # Check if it's from Home Assistant
                if 'homeassistant' in message.lower() or '192.168.2.' in message:
                    print("*** This appears to be from Home Assistant! ***")
                
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Port 514 Error: {e}")
                
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()

def check_relay_activity():
    """Monitor both ports simultaneously to debug relay"""
    
    print(f"Debugging relay - monitoring both ports simultaneously")
    print(f"Started at: {datetime.now()}")
    print("Press Ctrl+C to stop")
    
    # Create threads for each port
    thread_513 = threading.Thread(target=monitor_port_513, daemon=True)
    thread_514 = threading.Thread(target=monitor_port_514, daemon=True)
    
    # Start both threads
    thread_513.start()
    thread_514.start()
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

if __name__ == "__main__":
    check_relay_activity() 