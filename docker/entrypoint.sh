#!/bin/bash
set -e

# Enhanced TGE Monitor Entrypoint Script

echo "🚀 Starting Enhanced TGE Monitor"

# Wait for dependencies
echo "⏳ Waiting for dependencies..."

# Wait for PostgreSQL
if [ -n "$DATABASE_URL" ]; then
    echo "Waiting for PostgreSQL..."
    until python -c "
import psycopg2
import os
from urllib.parse import urlparse
url = os.environ['DATABASE_URL']
parsed = urlparse(url)
conn = psycopg2.connect(
    host=parsed.hostname,
    port=parsed.port,
    user=parsed.username,
    password=parsed.password,
    database=parsed.path[1:]
)
conn.close()
print('PostgreSQL is ready!')
" 2>/dev/null; do
        echo "PostgreSQL is unavailable - sleeping"
        sleep 2
    done
fi

# Wait for Redis
if [ -n "$REDIS_URL" ]; then
    echo "Waiting for Redis..."
    until python -c "
import redis
import os
from urllib.parse import urlparse
url = os.environ['REDIS_URL']
parsed = urlparse(url)
r = redis.Redis(
    host=parsed.hostname,
    port=parsed.port,
    password=parsed.password
)
r.ping()
print('Redis is ready!')
" 2>/dev/null; do
        echo "Redis is unavailable - sleeping"
        sleep 2
    done
fi

echo "✅ All dependencies are ready"

# Initialize database
echo "🔧 Initializing database..."
python -c "
from src.database import init_db
from src.auth import create_admin_user_if_not_exists
from src.database import DatabaseManager

try:
    init_db()
    print('✅ Database initialized')
    
    with DatabaseManager.get_session() as db:
        create_admin_user_if_not_exists(db)
    print('✅ Admin user created/verified')
    
except Exception as e:
    print(f'❌ Database initialization failed: {e}')
    exit(1)
"

# Migrate legacy data if exists
echo "📦 Checking for legacy data migration..."
python -c "
from src.database_service import migrate_from_file_storage
import os

if os.path.exists('state/monitor_state.json') or os.path.exists('state/twitter_state.json'):
    try:
        results = migrate_from_file_storage()
        print(f'✅ Legacy data migration: {results}')
    except Exception as e:
        print(f'⚠️ Legacy migration warning: {e}')
else:
    print('ℹ️ No legacy data found to migrate')
"

# Determine run mode
case "$1" in
    api)
        echo "🌐 Starting API server..."
        exec python -m uvicorn src.api:app \
            --host 0.0.0.0 \
            --port ${API_PORT:-8000} \
            --workers ${API_WORKERS:-1} \
            --loop uvloop \
            --http httptools
        ;;
    worker)
        echo "⚙️ Starting background worker..."
        exec python -m src.main_optimized_db --mode continuous
        ;;
    migrate)
        echo "📦 Running database migration..."
        python run_enhanced_system.py --mode migrate
        ;;
    test)
        echo "🧪 Running system tests..."
        python run_enhanced_system.py --mode test
        ;;
    demo)
        echo "🎭 Running demo mode..."
        python run_enhanced_system.py --mode demo
        ;;
    shell)
        echo "🐚 Starting shell..."
        exec /bin/bash
        ;;
    *)
        echo "Usage: $0 {api|worker|migrate|test|demo|shell}"
        echo "Available commands:"
        echo "  api     - Start the FastAPI server"
        echo "  worker  - Start the background monitoring worker"
        echo "  migrate - Run database migrations"
        echo "  test    - Run system tests"
        echo "  demo    - Run full demo mode"
        echo "  shell   - Start interactive shell"
        exit 1
        ;;
esac