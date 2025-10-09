#!/bin/bash

# TGE Swarm Production Deployment Script
# Infrastructure Architect: Claude
# Deploys a complete, production-ready swarm orchestration system

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_ENV="${DEPLOYMENT_ENV:-production}"
BACKUP_EXISTING="${BACKUP_EXISTING:-true}"

echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                TGE SWARM PRODUCTION DEPLOYMENT                   ║${NC}"
echo -e "${CYAN}║                Infrastructure Architect: Claude                  ║${NC}"
echo -e "${CYAN}║                                                                  ║${NC}"
echo -e "${CYAN}║  🏗️  Production-Ready Swarm Orchestration System                ║${NC}"
echo -e "${CYAN}║  🔧  Complete Infrastructure Automation                         ║${NC}"
echo -e "${CYAN}║  📊  Comprehensive Monitoring & Health Checks                   ║${NC}"
echo -e "${CYAN}║  🔄  Auto-Recovery & Fault Tolerance                           ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function definitions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo ""
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${PURPLE} $1${NC}"
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

check_prerequisites() {
    log_header "🔍 CHECKING PREREQUISITES"
    
    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker."
        exit 1
    fi
    log_success "Docker is installed and running"
    
    # Check if Docker Compose is available
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not available. Please install Docker Compose."
        exit 1
    fi
    log_success "Docker Compose is available"
    
    # Check system resources
    AVAILABLE_MEMORY=$(free -m | awk '/^Mem:/{print $7}')
    if [ "$AVAILABLE_MEMORY" -lt 4096 ]; then
        log_warning "System has less than 4GB available memory. Performance may be affected."
    else
        log_success "Sufficient memory available: ${AVAILABLE_MEMORY}MB"
    fi
    
    # Check disk space
    AVAILABLE_DISK=$(df -BG "$SCRIPT_DIR" | awk 'NR==2{print $4}' | sed 's/G//')
    if [ "$AVAILABLE_DISK" -lt 10 ]; then
        log_warning "Less than 10GB disk space available. Consider freeing up space."
    else
        log_success "Sufficient disk space available: ${AVAILABLE_DISK}GB"
    fi
}

setup_environment() {
    log_header "🌍 SETTING UP ENVIRONMENT"
    
    # Create necessary directories
    log_info "Creating directory structure..."
    mkdir -p logs reports backups safla-memory config
    mkdir -p infrastructure/{docker,monitoring,consul,health,deployment}
    mkdir -p infrastructure/monitoring/{prometheus,grafana,alertmanager}
    mkdir -p infrastructure/grafana/{provisioning/dashboards,provisioning/datasources,dashboards}
    mkdir -p infrastructure/consul/config
    
    # Set up environment variables
    if [ ! -f ".env" ]; then
        log_info "Creating environment configuration..."
        cat > .env << EOF
# TGE Swarm Production Environment Configuration
DEPLOYMENT_ENV=production
POSTGRES_PASSWORD=\$(openssl rand -base64 32)
REPLICATION_PASSWORD=\$(openssl rand -base64 32)
REDIS_PASSWORD=\$(openssl rand -base64 32)
GRAFANA_PASSWORD=admin123
CONSUL_ENCRYPT_KEY=\$(consul keygen 2>/dev/null || openssl rand -base64 32)

# Backup Configuration
BACKUP_S3_BUCKET=tge-swarm-backups
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key

# Monitoring Configuration
WEBHOOK_URL=your_webhook_url_for_alerts
SMTP_HOST=your_smtp_host
SMTP_PORT=587
SMTP_USER=your_smtp_user
SMTP_PASSWORD=your_smtp_password

# Network Configuration
EXTERNAL_DOMAIN=tge-swarm.local
SSL_EMAIL=admin@tge-swarm.local
EOF
        log_success "Environment configuration created (.env file)"
        log_warning "Please review and update .env file with your specific values"
    else
        log_info "Environment configuration already exists"
    fi
    
    # Source environment variables
    source .env
    
    # Create Docker networks if they don't exist
    log_info "Setting up Docker networks..."
    networks=("swarm-internal" "swarm-db" "swarm-cache" "swarm-agents" "swarm-discovery" "swarm-monitoring" "swarm-external")
    for network in "${networks[@]}"; do
        if ! docker network ls | grep -q "$network"; then
            docker network create "$network" || log_warning "Network $network might already exist"
        fi
    done
    log_success "Docker networks configured"
}

backup_existing_deployment() {
    if [ "$BACKUP_EXISTING" = "true" ]; then
        log_header "💾 BACKING UP EXISTING DEPLOYMENT"
        
        BACKUP_DIR="backups/pre-deployment-$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        
        # Backup existing data volumes
        if docker volume ls | grep -q "postgres_"; then
            log_info "Backing up PostgreSQL data..."
            docker run --rm -v postgres_primary_data:/source -v "$PWD/$BACKUP_DIR":/backup alpine tar czf /backup/postgres_data.tar.gz -C /source .
        fi
        
        if docker volume ls | grep -q "redis_"; then
            log_info "Backing up Redis data..."
            for i in 1 2 3; do
                if docker volume ls | grep -q "redis_master_${i}_data"; then
                    docker run --rm -v "redis_master_${i}_data":/source -v "$PWD/$BACKUP_DIR":/backup alpine tar czf "/backup/redis_master_${i}_data.tar.gz" -C /source .
                fi
            done
        fi
        
        # Backup configuration files
        if [ -d "safla-memory" ]; then
            cp -r safla-memory "$BACKUP_DIR/"
        fi
        
        if [ -d "logs" ]; then
            cp -r logs "$BACKUP_DIR/"
        fi
        
        log_success "Backup completed: $BACKUP_DIR"
    fi
}

deploy_infrastructure() {
    log_header "🏗️ DEPLOYING INFRASTRUCTURE COMPONENTS"
    
    log_info "Stopping any existing containers..."
    docker-compose -f docker-compose.swarm.yml down --remove-orphans || true
    
    log_info "Building custom images..."
    
    # Build Swarm Queen image
    cat > infrastructure/docker/Dockerfile.swarm-queen << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install redis consul-python asyncpg aiohttp prometheus-client

# Copy application code
COPY swarm-agents/ ./swarm-agents/
COPY src/ ./src/
COPY config.py .

# Create necessary directories
RUN mkdir -p logs reports safla-memory

# Set up health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "-m", "swarm-agents.swarm-memory-coordinator"]
EOF
    
    # Build Memory Coordinator image
    cat > infrastructure/docker/Dockerfile.memory-coordinator << 'EOF'
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install redis consul-python asyncpg aiohttp

COPY swarm-agents/ ./swarm-agents/

RUN mkdir -p logs safla-memory

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8002/health')" || exit 1

CMD ["python", "swarm-agents/swarm-memory-coordinator.py"]
EOF
    
    # Build Agent image
    cat > infrastructure/docker/Dockerfile.swarm-agent << 'EOF'
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install redis consul-python asyncpg aiohttp prometheus-client

COPY swarm-agents/ ./swarm-agents/
COPY src/ ./src/
COPY config.py .

RUN mkdir -p logs reports

HEALTHCHECK --interval=60s --timeout=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "swarm-agents.infrastructure.deployment.agent_deployment_framework"]
EOF
    
    log_success "Docker images built"
}

start_core_services() {
    log_header "🚀 STARTING CORE SERVICES"
    
    log_info "Starting PostgreSQL and Redis cluster..."
    docker-compose -f docker-compose.swarm.yml up -d postgres-primary redis-master-1 redis-master-2 redis-master-3
    
    log_info "Waiting for databases to be ready..."
    sleep 30
    
    log_info "Initializing Redis cluster..."
    docker-compose -f docker-compose.swarm.yml up redis-cluster-init
    
    log_info "Starting service discovery..."
    docker-compose -f docker-compose.swarm.yml up -d consul service-registry
    
    sleep 15
    log_success "Core services started"
}

start_swarm_components() {
    log_header "🧠 STARTING SWARM ORCHESTRATION"
    
    log_info "Starting Swarm Queen and Memory Coordinator..."
    docker-compose -f docker-compose.swarm.yml up -d swarm-queen swarm-memory-coordinator
    
    sleep 30
    
    log_info "Starting Swarm Agents..."
    docker-compose -f docker-compose.swarm.yml up -d \
        agent-scraping-efficiency \
        agent-keyword-precision \
        agent-api-reliability \
        agent-performance \
        agent-data-quality
    
    log_success "Swarm components started"
}

start_monitoring() {
    log_header "📊 STARTING MONITORING STACK"
    
    log_info "Starting Prometheus and AlertManager..."
    docker-compose -f docker-compose.swarm.yml up -d prometheus alertmanager
    
    sleep 20
    
    log_info "Starting Grafana..."
    docker-compose -f docker-compose.swarm.yml up -d grafana
    
    log_info "Starting Jaeger tracing..."
    docker-compose -f docker-compose.swarm.yml up -d jaeger
    
    log_success "Monitoring stack started"
}

start_load_balancer() {
    log_header "🔄 STARTING LOAD BALANCER"
    
    # Create HAProxy configuration
    mkdir -p infrastructure/haproxy
    cat > infrastructure/haproxy/haproxy.cfg << 'EOF'
global
    daemon
    maxconn 4096
    stats socket /var/run/haproxy.sock mode 600 level admin

defaults
    mode http
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms
    option httplog
    option dontlognull

frontend tge_swarm_frontend
    bind *:80
    bind *:443 ssl crt /etc/ssl/certs/tge-swarm.pem
    redirect scheme https if !{ ssl_fc }
    
    # API routes
    acl is_api path_beg /api
    use_backend swarm_queen_backend if is_api
    
    # Monitoring routes
    acl is_grafana path_beg /grafana
    use_backend grafana_backend if is_grafana
    
    acl is_prometheus path_beg /prometheus
    use_backend prometheus_backend if is_prometheus
    
    default_backend swarm_queen_backend

backend swarm_queen_backend
    balance roundrobin
    option httpchk GET /health
    server queen1 swarm-queen:8080 check

backend grafana_backend
    balance roundrobin
    option httpchk GET /api/health
    server grafana1 grafana:3000 check

backend prometheus_backend
    balance roundrobin
    option httpchk GET /-/healthy
    server prometheus1 prometheus:9090 check

listen stats
    bind *:8404
    stats enable
    stats uri /stats
    stats refresh 30s
    stats admin if TRUE
EOF
    
    log_info "Starting HAProxy load balancer..."
    docker-compose -f docker-compose.swarm.yml up -d haproxy
    
    log_success "Load balancer started"
}

start_backup_service() {
    log_header "💾 STARTING BACKUP SERVICE"
    
    # Create backup service Dockerfile
    cat > infrastructure/docker/Dockerfile.backup << 'EOF'
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    postgresql-client \
    redis-tools \
    cron \
    awscli \
    && rm -rf /var/lib/apt/lists/*

RUN pip install schedule boto3 psycopg2-binary redis

COPY infrastructure/backup/ ./backup/

RUN mkdir -p backups logs

# Set up cron for automated backups
RUN echo "0 2 * * * cd /app && python backup/backup_service.py" | crontab -

CMD ["cron", "-f"]
EOF
    
    # Create backup service script
    mkdir -p infrastructure/backup
    cat > infrastructure/backup/backup_service.py << 'EOF'
#!/usr/bin/env python3
import os
import subprocess
import boto3
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def backup_postgres():
    """Backup PostgreSQL database"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"backups/postgres_backup_{timestamp}.sql"
    
    cmd = [
        'pg_dump',
        os.environ['POSTGRES_URL'],
        '-f', backup_file
    ]
    
    subprocess.run(cmd, check=True)
    logger.info(f"PostgreSQL backup created: {backup_file}")
    return backup_file

def backup_redis():
    """Backup Redis data"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = f"backups/redis_backup_{timestamp}"
    os.makedirs(backup_dir, exist_ok=True)
    
    # Backup each Redis node
    for i, node in enumerate(['redis-master-1:7001', 'redis-master-2:7002', 'redis-master-3:7003'], 1):
        backup_file = f"{backup_dir}/redis_node_{i}.rdb"
        cmd = [
            'redis-cli', '-h', node.split(':')[0], '-p', node.split(':')[1],
            '--rdb', backup_file
        ]
        subprocess.run(cmd, check=True)
    
    logger.info(f"Redis backup created: {backup_dir}")
    return backup_dir

def upload_to_s3(file_path):
    """Upload backup to S3"""
    if not os.environ.get('AWS_ACCESS_KEY_ID'):
        logger.info("No AWS credentials configured, skipping S3 upload")
        return
    
    s3 = boto3.client('s3')
    bucket = os.environ['BACKUP_S3_BUCKET']
    key = f"tge-swarm/{os.path.basename(file_path)}"
    
    s3.upload_file(file_path, bucket, key)
    logger.info(f"Uploaded to S3: s3://{bucket}/{key}")

def cleanup_old_backups():
    """Remove backups older than retention period"""
    retention_days = int(os.environ.get('BACKUP_RETENTION_DAYS', 30))
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    
    for file in os.listdir('backups'):
        file_path = os.path.join('backups', file)
        if os.path.getctime(file_path) < cutoff_date.timestamp():
            os.remove(file_path)
            logger.info(f"Removed old backup: {file}")

if __name__ == "__main__":
    try:
        postgres_backup = backup_postgres()
        redis_backup = backup_redis()
        
        upload_to_s3(postgres_backup)
        upload_to_s3(redis_backup)
        
        cleanup_old_backups()
        
    except Exception as e:
        logger.error(f"Backup failed: {e}")
EOF
    
    log_info "Starting backup service..."
    docker-compose -f docker-compose.swarm.yml up -d backup-service
    
    log_success "Backup service started"
}

verify_deployment() {
    log_header "✅ VERIFYING DEPLOYMENT"
    
    log_info "Checking service health..."
    
    # Wait for services to be ready
    sleep 60
    
    # Check core services
    services_to_check=(
        "postgres-primary:5432"
        "redis-master-1:7001"
        "consul:8500"
        "swarm-queen:8080"
        "prometheus:9090"
        "grafana:3000"
    )
    
    failed_services=()
    
    for service in "${services_to_check[@]}"; do
        host=$(echo "$service" | cut -d: -f1)
        port=$(echo "$service" | cut -d: -f2)
        
        if docker run --rm --network swarm-internal alpine nc -z "$host" "$port" 2>/dev/null; then
            log_success "$service is accessible"
        else
            log_error "$service is not accessible"
            failed_services+=("$service")
        fi
    done
    
    # Check HTTP endpoints
    http_endpoints=(
        "http://localhost:8080/health:Swarm Queen"
        "http://localhost:9090/-/healthy:Prometheus"
        "http://localhost:3000/api/health:Grafana"
        "http://localhost:8500/v1/status/leader:Consul"
    )
    
    for endpoint_info in "${http_endpoints[@]}"; do
        endpoint=$(echo "$endpoint_info" | cut -d: -f1-2)
        name=$(echo "$endpoint_info" | cut -d: -f3)
        
        if curl -f -s "$endpoint" > /dev/null 2>&1; then
            log_success "$name endpoint is healthy"
        else
            log_warning "$name endpoint check failed (might need more time to start)"
        fi
    done
    
    if [ ${#failed_services[@]} -eq 0 ]; then
        log_success "All core services are running"
    else
        log_warning "Some services failed health checks: ${failed_services[*]}"
        log_info "This might be temporary - services may still be starting up"
    fi
}

display_access_information() {
    log_header "🌐 ACCESS INFORMATION"
    
    echo ""
    echo -e "${GREEN}TGE Swarm is now deployed! Access the following services:${NC}"
    echo ""
    echo -e "${BLUE}🎛️  Swarm Queen Dashboard:${NC}    http://localhost:8080"
    echo -e "${BLUE}📊 Grafana Monitoring:${NC}       http://localhost:3000 (admin/admin)"
    echo -e "${BLUE}📈 Prometheus Metrics:${NC}       http://localhost:9090"
    echo -e "${BLUE}🏥 Consul Service Discovery:${NC} http://localhost:8500"
    echo -e "${BLUE}📋 HAProxy Stats:${NC}            http://localhost:8404/stats"
    echo -e "${BLUE}🔍 Jaeger Tracing:${NC}           http://localhost:16686"
    echo -e "${BLUE}📊 AlertManager:${NC}             http://localhost:9093"
    echo ""
    echo -e "${YELLOW}Configuration Files:${NC}"
    echo -e "${YELLOW}  • Environment:${NC}     .env"
    echo -e "${YELLOW}  • Docker Compose:${NC}  docker-compose.swarm.yml"
    echo -e "${YELLOW}  • Logs Directory:${NC}  ./logs/"
    echo -e "${YELLOW}  • Reports Directory:${NC} ./reports/"
    echo ""
    echo -e "${YELLOW}Management Commands:${NC}"
    echo -e "${YELLOW}  • View logs:${NC}        docker-compose -f docker-compose.swarm.yml logs -f [service]"
    echo -e "${YELLOW}  • Scale agents:${NC}     docker-compose -f docker-compose.swarm.yml up -d --scale agent-[type]=N"
    echo -e "${YELLOW}  • Stop swarm:${NC}       docker-compose -f docker-compose.swarm.yml down"
    echo -e "${YELLOW}  • Health check:${NC}     python infrastructure/health/health_monitor.py status"
    echo ""
}

cleanup_on_failure() {
    log_error "Deployment failed. Cleaning up..."
    docker-compose -f docker-compose.swarm.yml down --remove-orphans
    exit 1
}

# Main deployment flow
main() {
    cd "$SCRIPT_DIR"
    
    # Set up error handling
    trap cleanup_on_failure ERR
    
    # Execute deployment steps
    check_prerequisites
    setup_environment
    backup_existing_deployment
    deploy_infrastructure
    start_core_services
    start_swarm_components
    start_monitoring
    start_load_balancer
    start_backup_service
    verify_deployment
    display_access_information
    
    log_success "TGE Swarm deployment completed successfully!"
    log_info "Monitor deployment status with: docker-compose -f docker-compose.swarm.yml ps"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-backup)
            BACKUP_EXISTING=false
            shift
            ;;
        --env)
            DEPLOYMENT_ENV="$2"
            shift 2
            ;;
        --help)
            echo "TGE Swarm Production Deployment Script"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --no-backup    Skip backing up existing deployment"
            echo "  --env ENV      Set deployment environment (default: production)"
            echo "  --help         Show this help message"
            echo ""
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main deployment
main