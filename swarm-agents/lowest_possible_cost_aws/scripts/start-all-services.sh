#!/bin/bash
# Startup script for TGE Swarm All-in-One container
# Cost Optimization Engineer: Claude

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

# Environment variables with defaults
export POSTGRES_URL=${POSTGRES_URL:-"postgresql://swarm_user:swarm_secure_pass@postgres:5432/tge_swarm"}
export REDIS_URL=${REDIS_URL:-"redis://:redis_secure_pass@redis:6379"}
export SAFLA_MEMORY_PATH=${SAFLA_MEMORY_PATH:-"/app/safla-memory"}
export LOG_LEVEL=${LOG_LEVEL:-"INFO"}
export OPTIMIZE_FOR_COST=${OPTIMIZE_FOR_COST:-"true"}

# TGE Configuration from config.py
export PYTHONPATH="/app:/app/swarm-agents:$PYTHONPATH"

log "Starting TGE Swarm All-in-One Services"
log "Cost optimization enabled: $OPTIMIZE_FOR_COST"

# Validate TGE configuration
log "Validating TGE configuration from config.py..."
python -c "
import sys
sys.path.append('/app')
sys.path.append('/app/swarm-agents')

try:
    import config
    validation_results = config.validate_config()
    
    total_configs = len(validation_results)
    valid_configs = sum(validation_results.values())
    
    print(f'Configuration validation: {valid_configs}/{total_configs} components valid')
    
    # Log specific validation results
    for component, is_valid in validation_results.items():
        status = 'VALID' if is_valid else 'INVALID'
        print(f'  {component}: {status}')
    
    # TGE monitoring will work with partial configuration
    print('TGE monitoring ready with available configuration')
    
except ImportError as e:
    print(f'Warning: Could not import config.py: {e}')
    print('TGE monitoring will use default settings')
except Exception as e:
    print(f'Warning: Configuration validation failed: {e}')
    print('TGE monitoring will continue with fallback settings')
"

# Create necessary directories
mkdir -p /app/logs /app/reports /app/safla-memory /app/backups

# Wait for dependencies
log "Waiting for dependencies..."

# Wait for PostgreSQL
log "Waiting for PostgreSQL..."
timeout=60
while ! pg_isready -h postgres -p 5432 -U swarm_user >/dev/null 2>&1; do
    timeout=$((timeout - 1))
    if [ $timeout -eq 0 ]; then
        error "PostgreSQL not available after 60 seconds"
        exit 1
    fi
    sleep 1
done
log "PostgreSQL is ready"

# Wait for Redis
log "Waiting for Redis..."
timeout=60
while ! redis-cli -h redis -p 6379 ping >/dev/null 2>&1; do
    timeout=$((timeout - 1))
    if [ $timeout -eq 0 ]; then
        error "Redis not available after 60 seconds"
        exit 1
    fi
    sleep 1
done
log "Redis is ready"

# Initialize database if needed
log "Checking database initialization..."
if ! psql "$POSTGRES_URL" -c "SELECT 1 FROM information_schema.tables WHERE table_name = 'agents' LIMIT 1;" >/dev/null 2>&1; then
    log "Initializing database schema..."
    python -c "
from swarm_agents.backend.database.models import Base
from sqlalchemy import create_engine
import os

engine = create_engine(os.getenv('POSTGRES_URL'))
Base.metadata.create_all(engine)
print('Database schema created successfully')
"
    log "Database schema initialized"
else
    log "Database schema already exists"
fi

# Set up cost optimization configurations
if [ "$OPTIMIZE_FOR_COST" = "true" ]; then
    log "Applying cost optimization settings..."
    
    # Reduce log levels for non-critical services
    export LOG_LEVEL="WARNING"
    
    # Enable batch processing
    export BATCH_OPERATIONS="true"
    export BATCH_SIZE="100"
    
    # Reduce polling frequencies
    export POLLING_INTERVAL="30"
    export HEALTH_CHECK_INTERVAL="60"
    
    # Optimize memory usage
    export MEMORY_LIMIT="1024M"
    export MAX_CONCURRENT_TASKS="10"
    
    log "Cost optimization settings applied"
fi

# Start cost monitoring in background
log "Starting cost monitoring..."
python /app/cost-optimizer.py &
COST_OPTIMIZER_PID=$!
log "Cost optimizer started (PID: $COST_OPTIMIZER_PID)"

# Function to handle shutdown
cleanup() {
    log "Shutting down services gracefully..."
    
    # Kill cost optimizer
    if [ -n "$COST_OPTIMIZER_PID" ]; then
        kill $COST_OPTIMIZER_PID 2>/dev/null || true
    fi
    
    # Stop all Python processes
    pkill -f "python.*swarm" || true
    
    log "Cleanup completed"
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Start all services via supervisor
log "Starting supervisor with all TGE Swarm services..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf