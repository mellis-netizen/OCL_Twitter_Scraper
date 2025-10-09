#!/bin/bash

# TGE Swarm Full Dashboard Startup Script
# Starts both the API server and React dashboard for complete monitoring solution

set -e

SCRIPT_DIR="$(dirname "$0")"
API_PORT=8080
DASHBOARD_PORT=3000

echo "🚀 Starting TGE Swarm Complete Dashboard Solution..."
echo "📁 Working directory: $SCRIPT_DIR"
echo ""

# Function to cleanup processes on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down dashboard services..."
    
    if [[ ! -z "$API_PID" ]]; then
        echo "   Stopping API server (PID: $API_PID)"
        kill $API_PID 2>/dev/null || true
    fi
    
    if [[ ! -z "$DASHBOARD_PID" ]]; then
        echo "   Stopping dashboard (PID: $DASHBOARD_PID)"
        kill $DASHBOARD_PID 2>/dev/null || true
    fi
    
    echo "👋 Dashboard services stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Check dependencies
echo "🔍 Checking dependencies..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.7+ to continue."
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16+ to continue."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "dashboard-api-server.py" ]; then
    echo "❌ dashboard-api-server.py not found. Please run from the swarm-agents directory."
    exit 1
fi

if [ ! -d "dashboard" ]; then
    echo "❌ Dashboard directory not found. Please ensure the React app is in ./dashboard/"
    exit 1
fi

echo "✅ Dependencies check passed"
echo ""

# Install Python dependencies
echo "📦 Installing Python dependencies for API server..."
python3 -m pip install aiohttp aiohttp-cors aiofiles pyyaml &>/dev/null || {
    echo "⚠️  Could not install Python dependencies. Some features may not work."
}

# Start API Server
echo "🌐 Starting API server on port $API_PORT..."
cd "$SCRIPT_DIR"
python3 dashboard-api-server.py --host 0.0.0.0 --port $API_PORT &
API_PID=$!

# Wait a moment for API server to start
sleep 3

# Check if API server is running
if ! kill -0 $API_PID 2>/dev/null; then
    echo "❌ Failed to start API server"
    exit 1
fi

echo "✅ API server started (PID: $API_PID)"
echo "   API endpoints: http://localhost:$API_PORT/api/"
echo "   WebSocket: ws://localhost:$API_PORT/ws"
echo ""

# Start Dashboard
echo "🎯 Starting React dashboard on port $DASHBOARD_PORT..."
cd "$SCRIPT_DIR/dashboard"

# Install npm dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing Node.js dependencies..."
    npm install --silent
fi

# Create environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
REACT_APP_API_URL=http://localhost:$API_PORT/api
REACT_APP_WS_URL=ws://localhost:$API_PORT
EOF
fi

# Start the dashboard
export PORT=$DASHBOARD_PORT
npm start &
DASHBOARD_PID=$!

# Wait a moment for dashboard to start
sleep 5

# Check if dashboard is running
if ! kill -0 $DASHBOARD_PID 2>/dev/null; then
    echo "❌ Failed to start React dashboard"
    cleanup
    exit 1
fi

echo "✅ React dashboard started (PID: $DASHBOARD_PID)"
echo ""

# Show access information
echo "🎉 TGE Swarm Dashboard is now running!"
echo ""
echo "📊 Dashboard URL: http://localhost:$DASHBOARD_PORT"
echo "🔌 API Server:    http://localhost:$API_PORT"
echo "🌐 WebSocket:     ws://localhost:$API_PORT/ws"
echo ""
echo "📋 Available Features:"
echo "   • Real-time agent monitoring"
echo "   • Performance metrics and charts" 
echo "   • Log viewer with filtering"
echo "   • Agent control (start/stop/restart)"
echo "   • System health overview"
echo "   • Configuration management"
echo ""
echo "⏹️  Press Ctrl+C to stop all services"
echo ""

# Wait for processes
wait $API_PID $DASHBOARD_PID