#!/bin/bash

# Docker deployment script for Crypto TGE Monitor
# Provides easy deployment and management using Docker Compose

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
ENV_FILE="$PROJECT_ROOT/.env"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check dependencies
check_dependencies() {
    log "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
    fi
    
    # Determine compose command
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    log "Dependencies check passed"
}

# Check environment file
check_env_file() {
    log "Checking environment configuration..."
    
    if [ ! -f "$ENV_FILE" ]; then
        warn "Environment file not found at $ENV_FILE"
        info "Creating template environment file..."
        
        cat > "$ENV_FILE" << 'EOF'
# Email Configuration (Required)
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
RECIPIENT_EMAIL=recipient@example.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Twitter API Configuration (Optional)
TWITTER_BEARER_TOKEN=your-bearer-token

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/var/log/crypto-tge-monitor/crypto_monitor.log

# System Configuration
DISABLE_TWITTER=0
TWITTER_ENABLE_SEARCH=1
EOF
        
        warn "Please edit $ENV_FILE with your configuration before proceeding"
        info "After editing the file, run: $0 deploy"
        exit 1
    fi
    
    # Check if template values are still present
    if grep -q "your-email@gmail.com\|your-app-password\|your-bearer-token" "$ENV_FILE"; then
        warn "Environment file contains template values"
        warn "Please update $ENV_FILE with your actual configuration"
        exit 1
    fi
    
    log "Environment configuration validated"
}

# Build images
build_images() {
    log "Building Docker images..."
    
    cd "$PROJECT_ROOT"
    $COMPOSE_CMD -f "$COMPOSE_FILE" build --no-cache
    
    log "Docker images built successfully"
}

# Deploy services
deploy() {
    log "Deploying Crypto TGE Monitor services..."
    
    cd "$PROJECT_ROOT"
    
    # Stop existing services
    $COMPOSE_CMD -f "$COMPOSE_FILE" down
    
    # Start services
    $COMPOSE_CMD -f "$COMPOSE_FILE" up -d
    
    # Wait for services to be healthy
    log "Waiting for services to start..."
    sleep 30
    
    # Check service status
    show_status
    
    log "Deployment completed successfully!"
}

# Show service status
show_status() {
    info "Service Status:"
    $COMPOSE_CMD -f "$COMPOSE_FILE" ps
    
    echo ""
    info "Health Checks:"
    
    # Check main application
    if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Application health check: PASSED${NC}"
    else
        echo -e "${RED}✗ Application health check: FAILED${NC}"
    fi
    
    # Check NGINX
    if curl -sf http://localhost/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ NGINX health check: PASSED${NC}"
    else
        echo -e "${RED}✗ NGINX health check: FAILED${NC}"
    fi
    
    echo ""
    info "Available Endpoints:"
    echo "  http://localhost/health     - Basic health check"
    echo "  http://localhost/status     - Detailed status"
    echo "  http://localhost/metrics    - Prometheus metrics"
    echo "  http://localhost:3000       - Grafana dashboard (admin/admin)"
    echo "  http://localhost:9090       - Prometheus UI"
}

# Show logs
show_logs() {
    local service=${1:-crypto-tge-monitor}
    log "Showing logs for $service..."
    $COMPOSE_CMD -f "$COMPOSE_FILE" logs -f "$service"
}

# Stop services
stop() {
    log "Stopping services..."
    $COMPOSE_CMD -f "$COMPOSE_FILE" down
    log "Services stopped"
}

# Restart services
restart() {
    log "Restarting services..."
    $COMPOSE_CMD -f "$COMPOSE_FILE" restart
    show_status
}

# Update services
update() {
    log "Updating services..."
    
    # Pull latest images
    $COMPOSE_CMD -f "$COMPOSE_FILE" pull
    
    # Rebuild custom images
    build_images
    
    # Restart services
    $COMPOSE_CMD -f "$COMPOSE_FILE" up -d
    
    show_status
    log "Update completed"
}

# Backup data
backup() {
    log "Creating backup..."
    
    local backup_dir="$PROJECT_ROOT/backups"
    local backup_file="$backup_dir/crypto-tge-backup-$(date +%Y%m%d_%H%M%S).tar.gz"
    
    mkdir -p "$backup_dir"
    
    # Create backup of volumes
    docker run --rm \
        -v crypto-tge-state:/data/state:ro \
        -v crypto-tge-logs:/data/logs:ro \
        -v "$backup_dir":/backup \
        busybox tar -czf "/backup/$(basename "$backup_file")" -C /data .
    
    log "Backup created: $backup_file"
}

# Restore from backup
restore() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ] || [ ! -f "$backup_file" ]; then
        error "Backup file not specified or does not exist"
    fi
    
    log "Restoring from backup: $backup_file"
    
    # Stop services
    $COMPOSE_CMD -f "$COMPOSE_FILE" down
    
    # Restore backup
    docker run --rm \
        -v crypto-tge-state:/data/state \
        -v crypto-tge-logs:/data/logs \
        -v "$(dirname "$backup_file")":/backup:ro \
        busybox tar -xzf "/backup/$(basename "$backup_file")" -C /data
    
    # Start services
    $COMPOSE_CMD -f "$COMPOSE_FILE" up -d
    
    log "Restore completed"
}

# Cleanup old images and volumes
cleanup() {
    log "Cleaning up Docker resources..."
    
    # Remove unused images
    docker image prune -f
    
    # Remove unused volumes (be careful!)
    read -p "Remove unused volumes? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker volume prune -f
    fi
    
    log "Cleanup completed"
}

# Show help
show_help() {
    echo "Docker Deployment Script for Crypto TGE Monitor"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  deploy          Deploy the application stack"
    echo "  build           Build Docker images"
    echo "  status          Show service status"
    echo "  logs [service]  Show logs (default: crypto-tge-monitor)"
    echo "  stop            Stop all services"
    echo "  restart         Restart all services"
    echo "  update          Update and restart services"
    echo "  backup          Create backup of application data"
    echo "  restore <file>  Restore from backup file"
    echo "  cleanup         Clean up unused Docker resources"
    echo "  help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 deploy                               # Deploy the application"
    echo "  $0 logs                                 # Show application logs"
    echo "  $0 logs nginx                           # Show NGINX logs"
    echo "  $0 backup                               # Create backup"
    echo "  $0 restore backups/backup-file.tar.gz  # Restore from backup"
}

# Main function
main() {
    local command=${1:-help}
    
    case $command in
        deploy)
            check_dependencies
            check_env_file
            build_images
            deploy
            ;;
        build)
            check_dependencies
            build_images
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "$2"
            ;;
        stop)
            stop
            ;;
        restart)
            restart
            ;;
        update)
            check_dependencies
            update
            ;;
        backup)
            backup
            ;;
        restore)
            restore "$2"
            ;;
        cleanup)
            cleanup
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"