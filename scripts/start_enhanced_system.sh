#!/bin/bash
# Enhanced TGE Monitor Startup Script

echo "Starting Enhanced TGE Monitor System..."

# Set environment variables
export DATABASE_URL="postgresql://computer@localhost:5432/tge_monitor"
export REDIS_URL="redis://localhost:6379/0"
export SECRET_KEY="your-production-secret-key"
export API_PORT="8000"
export LOG_LEVEL="INFO"

# Start the system
python run_enhanced_system.py --mode production

echo "Enhanced TGE Monitor System started"
