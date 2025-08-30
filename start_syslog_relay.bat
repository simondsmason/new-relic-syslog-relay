@echo off
title Syslog Relay v1.27
echo Starting Syslog Relay v1.27...
echo.
echo The relay will start in the system tray.
echo Right-click the tray icon to stop the relay.
echo.

cd /d "%~dp0"
python syslog_relay_tray.py

echo.
echo Relay has stopped.
echo Press any key to exit...
pause >nul 