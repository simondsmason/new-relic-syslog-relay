@echo off
title Deploy Syslog Relay to Desktop
echo Deploying Syslog Relay files to Desktop execution folder...
echo.

echo Deleting existing files...
if exist "C:\Users\simon\Desktop\Syslog Relay\syslog_relay_tray.py" (
    del "C:\Users\simon\Desktop\Syslog Relay\syslog_relay_tray.py"
    echo ✓ Deleted old syslog_relay_tray.py
)
if exist "C:\Users\simon\Desktop\Syslog Relay\start_syslog_relay.bat" (
    del "C:\Users\simon\Desktop\Syslog Relay\start_syslog_relay.bat"
    echo ✓ Deleted old start_syslog_relay.bat
)
if exist "C:\Users\simon\Desktop\Syslog Relay\requirements.txt" (
    del "C:\Users\simon\Desktop\Syslog Relay\requirements.txt"
    echo ✓ Deleted old requirements.txt
)

echo.
echo Copying new files...

echo Copying syslog_relay_tray.py...
copy "syslog_relay_tray.py" "C:\Users\simon\Desktop\Syslog Relay\syslog_relay_tray.py" /Y
if %errorlevel% equ 0 (
    echo ✓ syslog_relay_tray.py copied successfully
) else (
    echo ✗ Failed to copy syslog_relay_tray.py
)

echo.
echo Copying start_syslog_relay.bat...
copy "start_syslog_relay.bat" "C:\Users\simon\Desktop\Syslog Relay\start_syslog_relay.bat" /Y
if %errorlevel% equ 0 (
    echo ✓ start_syslog_relay.bat copied successfully
) else (
    echo ✗ Failed to copy start_syslog_relay.bat
)

echo.
echo Copying requirements.txt...
copy "requirements.txt" "C:\Users\simon\Desktop\Syslog Relay\requirements.txt" /Y
if %errorlevel% equ 0 (
    echo ✓ requirements.txt copied successfully
) else (
    echo ✗ Failed to copy requirements.txt
)

echo.
echo Deployment complete!
echo.
echo Files deployed to: C:\Users\simon\Desktop\Syslog Relay\
echo.
pause
