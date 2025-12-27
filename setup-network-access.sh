#!/bin/bash

echo "==================================="
echo "Network Access Configuration"
echo "==================================="
echo ""

# Get local IP address
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "localhost")
else
    # Linux
    LOCAL_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")
fi

echo "Your local IP address: $LOCAL_IP"
echo ""
echo "This script will update your .env file to allow"
echo "network access from other devices."
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

echo ""
echo "Backing up current .env file..."
if [ -f .env ]; then
    cp .env .env.backup
    echo "✓ Backup created: .env.backup"
else
    echo "⚠ No .env file found, copying from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
    else
        echo "✗ Error: Neither .env nor .env.example found!"
        exit 1
    fi
fi

echo ""
echo "Updating CORS_ORIGINS in .env file..."

# Update CORS_ORIGINS line
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS (BSD sed)
    sed -i '' "s|CORS_ORIGINS=.*|CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://$LOCAL_IP:3000,http://$LOCAL_IP:3001,http://127.0.0.1:3000|g" .env
else
    # Linux (GNU sed)
    sed -i "s|CORS_ORIGINS=.*|CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://$LOCAL_IP:3000,http://$LOCAL_IP:3001,http://127.0.0.1:3000|g" .env
fi

echo "✓ CORS_ORIGINS updated to include:"
echo "  - http://localhost:3000"
echo "  - http://$LOCAL_IP:3000"
echo "  - http://127.0.0.1:3000"
echo ""

echo "Configuring Firewall..."
echo ""

# Try to configure firewall based on OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "⚠ macOS detected - Firewall configuration:"
    echo "  1. Open System Preferences > Security & Privacy > Firewall"
    echo "  2. Click 'Firewall Options'"
    echo "  3. Add Python to allowed applications"
    echo ""
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Check if ufw is available (Ubuntu/Debian)
    if command -v ufw &> /dev/null; then
        echo "Configuring UFW firewall..."
        sudo ufw allow 8000/tcp comment "Mufu Farm Backend" 2>/dev/null && echo "✓ Port 8000 allowed" || echo "⚠ Could not configure port 8000"
        sudo ufw allow 3000/tcp comment "Mufu Farm Frontend" 2>/dev/null && echo "✓ Port 3000 allowed" || echo "⚠ Could not configure port 3000"
    # Check if firewalld is available (Fedora/CentOS/RHEL)
    elif command -v firewall-cmd &> /dev/null; then
        echo "Configuring firewalld..."
        sudo firewall-cmd --permanent --add-port=8000/tcp 2>/dev/null && echo "✓ Port 8000 allowed" || echo "⚠ Could not configure port 8000"
        sudo firewall-cmd --permanent --add-port=3000/tcp 2>/dev/null && echo "✓ Port 3000 allowed" || echo "⚠ Could not configure port 3000"
        sudo firewall-cmd --reload 2>/dev/null
    else
        echo "⚠ No known firewall manager found. Please configure manually:"
        echo "  Allow incoming connections on ports 3000 and 8000"
    fi
else
    echo "⚠ Unknown OS - Please configure firewall manually"
fi

echo ""
echo "==================================="
echo "Configuration Complete!"
echo "==================================="
echo ""
echo "Your application is now configured for network access."
echo ""
echo "To start the servers, run: ./start-dev.sh"
echo ""
echo "Other devices can access:"
echo "  Frontend: http://$LOCAL_IP:3000"
echo "  Backend:  http://$LOCAL_IP:8000"
echo "  API Docs: http://$LOCAL_IP:8000/docs"
echo ""
echo "IMPORTANT: Make sure all devices are on the same network!"
echo ""
echo "For more details, see: NETWORK_ACCESS.md"
echo ""

