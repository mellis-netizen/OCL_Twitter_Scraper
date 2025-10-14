#!/bin/bash
# TGE Swarm Stop Script
# Gracefully stops the swarm backend

echo "=========================================="
echo "Stopping TGE Swarm Backend"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Check if PID file exists
if [ -f ".swarm_backend.pid" ]; then
    PID=$(cat .swarm_backend.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "Stopping backend (PID: $PID)..."
        kill -TERM $PID

        # Wait for graceful shutdown
        for i in {1..10}; do
            if ! ps -p $PID > /dev/null 2>&1; then
                echo -e "${GREEN}✓ Backend stopped gracefully${NC}"
                rm .swarm_backend.pid
                exit 0
            fi
            sleep 1
        done

        # Force kill if still running
        echo "Forcing shutdown..."
        kill -9 $PID 2>/dev/null || true
        rm .swarm_backend.pid
        echo -e "${GREEN}✓ Backend stopped${NC}"
    else
        echo "Backend not running (stale PID file)"
        rm .swarm_backend.pid
    fi
else
    # Try to find process without PID file
    if pgrep -f "python.*swarm_backend.py" > /dev/null; then
        echo "Found running backend without PID file"
        pkill -TERM -f "python.*swarm_backend.py"
        sleep 2
        echo -e "${GREEN}✓ Backend stopped${NC}"
    else
        echo "No running backend found"
    fi
fi
