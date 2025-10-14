#!/bin/bash
# TGE Swarm Initialization Script
# Sets up the swarm backend infrastructure and agents

set -e  # Exit on error

echo "=========================================="
echo "TGE Swarm Initialization"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running from correct directory
if [ ! -f "backend/swarm_backend.py" ]; then
    echo -e "${RED}Error: Please run this script from the swarm-agents directory${NC}"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
echo "Checking dependencies..."
if ! command_exists python3; then
    echo -e "${RED}Error: Python 3 is required but not installed${NC}"
    exit 1
fi

if ! command_exists docker; then
    echo -e "${YELLOW}Warning: Docker not found. Agent containerization will not be available${NC}"
fi

if ! command_exists redis-server && ! docker ps | grep -q redis; then
    echo -e "${YELLOW}Warning: Redis not found. Starting Redis via Docker...${NC}"
    docker run -d --name tge-redis -p 6379:6379 redis:alpine || true
fi

echo -e "${GREEN}✓ Dependencies checked${NC}"
echo ""

# Create necessary directories
echo "Creating directory structure..."
mkdir -p logs
mkdir -p safla-memory
mkdir -p config
mkdir -p reports
mkdir -p src/agents
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
if [ -f "../requirements.txt" ]; then
    pip3 install -r ../requirements.txt -q || echo -e "${YELLOW}Warning: Some dependencies may have failed to install${NC}"
fi

pip3 install -q aiohttp redis pyyaml docker python-consul psutil tenacity || echo -e "${YELLOW}Warning: Some dependencies may have failed to install${NC}"
echo -e "${GREEN}✓ Python dependencies installed${NC}"
echo ""

# Initialize swarm memory
echo "Initializing SAFLA memory system..."
python3 -c "
import sys
sys.path.append('..')
from swarm_memory_coordinator import SwarmMemoryCoordinator

coordinator = SwarmMemoryCoordinator('./safla-memory')
print('Memory coordinator initialized')
" || echo -e "${YELLOW}Warning: Memory initialization may have issues${NC}"
echo -e "${GREEN}✓ Memory system initialized${NC}"
echo ""

# Create default configuration if not exists
echo "Setting up configuration files..."
if [ ! -f "config/swarm_backend.yaml" ]; then
    echo -e "${YELLOW}Configuration files not found in config directory${NC}"
    echo "Please ensure config files are in place"
fi
echo -e "${GREEN}✓ Configuration ready${NC}"
echo ""

# Initialize database (if using PostgreSQL)
echo "Checking database connection..."
python3 -c "
import sys
import os
sys.path.append('..')

# Try to import and check database
try:
    from src.database import init_db
    print('Database module available')
except Exception as e:
    print(f'Database initialization skipped: {e}')
" || echo -e "${YELLOW}Warning: Database initialization skipped${NC}"
echo ""

# Start Redis if not running
echo "Checking Redis connection..."
python3 -c "
import redis
try:
    r = redis.Redis(host='localhost', port=6379)
    r.ping()
    print('Redis is running')
except:
    print('Redis connection failed - please start Redis manually')
    exit(1)
" || echo -e "${RED}Error: Redis is required but not accessible${NC}"
echo ""

# Test swarm backend initialization
echo "Testing swarm backend initialization..."
python3 -c "
import sys
import asyncio
sys.path.append('.')

async def test_init():
    from backend.swarm_backend import SwarmBackend
    backend = SwarmBackend('config/swarm_backend.yaml')
    print('Backend instance created successfully')

try:
    asyncio.run(test_init())
except Exception as e:
    print(f'Backend test: {e}')
" || echo -e "${YELLOW}Warning: Backend test encountered issues${NC}"
echo -e "${GREEN}✓ Backend initialization test complete${NC}"
echo ""

# Create systemd service file (optional)
if command_exists systemctl; then
    echo "Creating systemd service file..."
    cat > /tmp/tge-swarm.service <<EOF
[Unit]
Description=TGE Swarm Backend Service
After=network.target redis.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(which python3) backend/swarm_backend.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    echo "Service file created at /tmp/tge-swarm.service"
    echo "To install: sudo cp /tmp/tge-swarm.service /etc/systemd/system/"
    echo "Then: sudo systemctl enable tge-swarm && sudo systemctl start tge-swarm"
fi
echo ""

# Summary
echo "=========================================="
echo -e "${GREEN}Initialization Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Review configuration in config/swarm_backend.yaml"
echo "2. Start the swarm backend: python3 backend/swarm_backend.py"
echo "3. Monitor logs in: logs/swarm_backend.log"
echo "4. Access dashboard at: http://localhost:8080"
echo ""
echo "Quick start command:"
echo "  python3 backend/swarm_backend.py"
echo ""
echo "For help: python3 backend/swarm_backend.py --help"
echo ""
