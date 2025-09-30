#!/bin/bash


echo "Starting Crypto TGE Monitor - Production Mode"
echo "================================================"
echo ""
echo "Configuration:"
echo "- Schedule: Every Monday at 8:00 AM PST (16:00 UTC)"
echo "- Summary: Every Monday at 8:30 AM PST (16:30 UTC)"
echo "- Log file: logs/crypto_monitor.log"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create .env file with your configuration."
    echo "See .env.example for reference."
    exit 1
fi

# Create required directories
mkdir -p state logs

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "❌ Error: Python not found!"
    exit 1
fi

echo "Using Python: $PYTHON"
echo ""

# Install dependencies if needed
echo "Checking dependencies..."
$PYTHON -c "import requests, feedparser, schedule, tweepy, psutil" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing dependencies..."
    $PYTHON -m pip install -r requirements.txt
fi

echo ""
echo "Starting monitor in continuous mode..."
echo "Press Ctrl+C to stop"
echo ""

# Run the monitor
exec $PYTHON src/main.py --mode continuous