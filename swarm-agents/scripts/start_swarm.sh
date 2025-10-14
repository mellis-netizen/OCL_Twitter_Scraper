#!/bin/bash
# TGE Swarm Startup Script
# Starts the swarm backend and all services

set -e

echo "=========================================="
echo "Starting TGE Swarm Backend"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if already running
if pgrep -f "python.*swarm_backend.py" > /dev/null; then
    echo -e "${YELLOW}Warning: Swarm backend appears to be already running${NC}"
    echo "PID: $(pgrep -f 'python.*swarm_backend.py')"
    read -p "Stop existing instance and restart? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pkill -f "python.*swarm_backend.py" || true
        sleep 2
    else
        exit 0
    fi
fi

# Check Redis
echo "Checking Redis..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo -e "${YELLOW}Redis not responding, attempting to start...${NC}"
    if command -v redis-server > /dev/null; then
        redis-server --daemonize yes
        sleep 2
    elif command -v docker > /dev/null; then
        docker run -d --name tge-redis -p 6379:6379 redis:alpine || true
        sleep 3
    else
        echo -e "${RED}Error: Redis is required but not available${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✓ Redis is running${NC}"

# Check configuration
if [ ! -f "config/swarm_backend.yaml" ]; then
    echo -e "${RED}Error: config/swarm_backend.yaml not found${NC}"
    exit 1
fi

# Create necessary directories
mkdir -p logs
mkdir -p safla-memory
mkdir -p reports

# Start backend
echo ""
echo "Starting swarm backend..."
echo "Configuration: config/swarm_backend.yaml"
echo "Logs: logs/swarm_backend.log"
echo ""

# Run in background or foreground
if [ "$1" == "--daemon" ] || [ "$1" == "-d" ]; then
    echo "Starting in daemon mode..."
    nohup python3 backend/swarm_backend.py > logs/swarm_backend.log 2>&1 &
    BACKEND_PID=$!
    echo "Backend started with PID: $BACKEND_PID"
    echo $BACKEND_PID > .swarm_backend.pid

    # Wait a moment and check if still running
    sleep 3
    if ps -p $BACKEND_PID > /dev/null; then
        echo -e "${GREEN}✓ Backend started successfully${NC}"
        echo ""
        echo "Dashboard: http://localhost:8080"
        echo "WebSocket: ws://localhost:8080/ws"
        echo ""
        echo "To stop: ./scripts/stop_swarm.sh"
        echo "To view logs: tail -f logs/swarm_backend.log"
    else
        echo -e "${RED}Error: Backend failed to start${NC}"
        echo "Check logs/swarm_backend.log for details"
        exit 1
    fi
else
    echo "Starting in foreground mode (Ctrl+C to stop)..."
    echo ""
    python3 backend/swarm_backend.py
fi
