@echo off
echo ===================================
echo Network Access Configuration
echo ===================================
echo.

REM Get local IP address
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    set LOCAL_IP=%%a
    goto :found
)
:found
set LOCAL_IP=%LOCAL_IP:~1%

echo Your local IP address: %LOCAL_IP%
echo.
echo This script will update your .env file to allow
echo network access from other devices.
echo.
echo Press any key to continue or Ctrl+C to cancel...
pause > nul

echo.
echo Backing up current .env file...
if exist .env (
    copy .env .env.backup > nul
    echo ✓ Backup created: .env.backup
) else (
    echo ⚠ No .env file found, copying from .env.example...
    if exist .env.example (
        copy .env.example .env > nul
    ) else (
        echo ✗ Error: Neither .env nor .env.example found!
        pause
        exit /b 1
    )
)

echo.
echo Updating CORS_ORIGINS in .env file...

REM Create temporary file with updated CORS
powershell -Command "(Get-Content .env) -replace 'CORS_ORIGINS=.*', 'CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://%LOCAL_IP%:3000,http://%LOCAL_IP%:3001,http://127.0.0.1:3000' | Set-Content .env.tmp"
move /Y .env.tmp .env > nul

echo ✓ CORS_ORIGINS updated to include:
echo   - http://localhost:3000
echo   - http://%LOCAL_IP%:3000
echo   - http://127.0.0.1:3000
echo.

echo Configuring Windows Firewall...
echo.
echo NOTE: This requires Administrator privileges.
echo If prompted, click 'Yes' to allow.
echo.

REM Try to add firewall rules (requires admin)
netsh advfirewall firewall add rule name="Mufu Farm Backend (Port 8000)" dir=in action=allow protocol=TCP localport=8000 > nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ Firewall rule added for Backend (Port 8000)
) else (
    echo ⚠ Could not add firewall rule automatically.
    echo   Please add manually or run this script as Administrator.
)

netsh advfirewall firewall add rule name="Mufu Farm Frontend (Port 3000)" dir=in action=allow protocol=TCP localport=3000 > nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ Firewall rule added for Frontend (Port 3000)
) else (
    echo ⚠ Could not add firewall rule automatically.
    echo   Please add manually or run this script as Administrator.
)

echo.
echo ===================================
echo Configuration Complete!
echo ===================================
echo.
echo Your application is now configured for network access.
echo.
echo To start the servers, run: start-dev.bat
echo.
echo Other devices can access:
echo   Frontend: http://%LOCAL_IP%:3000
echo   Backend:  http://%LOCAL_IP%:8000
echo   API Docs: http://%LOCAL_IP%:8000/docs
echo.
echo IMPORTANT: Make sure all devices are on the same network!
echo.
echo For more details, see: NETWORK_ACCESS.md
echo.
pause

