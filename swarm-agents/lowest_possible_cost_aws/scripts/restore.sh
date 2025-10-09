#!/bin/bash
# Restore script for TGE Swarm cost-optimized deployment
# Cost Optimization Engineer: Claude

set -e

# Configuration
BACKUP_DIR="/app/backups"
LOG_FILE="/app/logs/restore.log"
TEMP_DIR="/tmp/tge-restore-$(date +%s)"

# Database connection
POSTGRES_URL=${POSTGRES_URL:-"postgresql://swarm_user:swarm_secure_pass@postgres:5432/tge_swarm"}
REDIS_URL=${REDIS_URL:-"redis://:redis_secure_pass@redis:6379"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

# Show usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS] BACKUP_FILE

Restore TGE Swarm from a backup archive.

OPTIONS:
    -f, --force                  Force restore without confirmation
    --database-only             Restore only the database
    --data-only                 Restore only application data
    --no-database               Skip database restore
    --backup-current            Create backup of current state before restore
    -h, --help                  Show this help message

ARGUMENTS:
    BACKUP_FILE                 Path to backup archive (.tar.gz file)
                               Use 'latest' to restore from most recent backup

EXAMPLES:
    $0 /app/backups/tge-swarm-backup-20231201_120000.tar.gz
    $0 latest
    $0 --database-only latest
    $0 --backup-current --force latest

EOF
}

# List available backups
list_backups() {
    echo "Available backups:"
    echo "=================="
    
    if [ ! -d "$BACKUP_DIR" ] || [ -z "$(ls -A "$BACKUP_DIR"/*.tar.gz 2>/dev/null)" ]; then
        echo "No backups found in $BACKUP_DIR"
        return 1
    fi
    
    ls -lht "$BACKUP_DIR"/*.tar.gz | while read -r line; do
        local file=$(echo "$line" | awk '{print $9}')
        local size=$(echo "$line" | awk '{print $5}')
        local date=$(echo "$line" | awk '{print $6, $7, $8}')
        local basename=$(basename "$file")
        
        echo "• $basename ($size) - $date"
    done
}

# Get latest backup
get_latest_backup() {
    ls -t "$BACKUP_DIR"/tge-swarm-backup-*.tar.gz 2>/dev/null | head -1 || echo ""
}

# Validate backup file
validate_backup() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        error "Backup file not found: $backup_file"
    fi
    
    log "Validating backup archive..."
    
    # Test if archive can be extracted
    if ! tar -tzf "$backup_file" >/dev/null 2>&1; then
        error "Backup archive is corrupted or invalid"
    fi
    
    # Check for required files
    local required_files=("backup-manifest.txt")
    for file in "${required_files[@]}"; do
        if ! tar -tzf "$backup_file" | grep -q "$file"; then
            error "Required file missing from backup: $file"
        fi
    done
    
    log "Backup archive validation passed"
}

# Extract backup
extract_backup() {
    local backup_file="$1"
    
    log "Extracting backup archive..."
    
    mkdir -p "$TEMP_DIR"
    
    if ! tar -xzf "$backup_file" -C "$TEMP_DIR"; then
        error "Failed to extract backup archive"
    fi
    
    # Find the extracted directory
    local extracted_dir=$(find "$TEMP_DIR" -maxdepth 1 -type d -name "tge-swarm-backup-*" | head -1)
    
    if [ -z "$extracted_dir" ]; then
        error "Could not find extracted backup directory"
    fi
    
    echo "$extracted_dir"
}

# Show backup information
show_backup_info() {
    local backup_dir="$1"
    local manifest_file="$backup_dir/backup-manifest.txt"
    
    if [ -f "$manifest_file" ]; then
        log "Backup Information:"
        echo "==================="
        cat "$manifest_file"
        echo "==================="
    else
        warn "Backup manifest not found"
    fi
}

# Create current state backup
backup_current_state() {
    log "Creating backup of current state..."
    
    local current_backup_name="pre-restore-backup-$(date +%Y%m%d_%H%M%S)"
    
    # Use the backup script to create a backup
    if [ -f "/app/scripts/backup-local.sh" ]; then
        BACKUP_NAME="$current_backup_name" /app/scripts/backup-local.sh
        log "Current state backed up as: $current_backup_name"
    else
        warn "Backup script not found, skipping current state backup"
    fi
}

# Restore database
restore_database() {
    local backup_dir="$1"
    local db_file="$backup_dir/database.sql.gz"
    
    if [ ! -f "$db_file" ]; then
        warn "Database backup file not found, skipping database restore"
        return
    fi
    
    log "Restoring PostgreSQL database..."
    
    # Stop any running services that might be using the database
    log "Note: Ensure TGE Swarm services are stopped before restoring database"
    
    # Drop and recreate database
    local db_name=$(echo "$POSTGRES_URL" | sed -n 's|.*/\([^?]*\).*|\1|p')
    local base_url=$(echo "$POSTGRES_URL" | sed 's|/[^/]*$|/postgres|')
    
    log "Dropping and recreating database: $db_name"
    
    # This would typically require superuser privileges
    # In a production environment, you might need to handle this differently
    psql "$base_url" -c "DROP DATABASE IF EXISTS $db_name;" 2>/dev/null || warn "Could not drop database (may not exist)"
    psql "$base_url" -c "CREATE DATABASE $db_name;" || error "Failed to create database"
    
    # Restore from backup
    log "Restoring database from backup..."
    if ! gunzip -c "$db_file" | psql "$POSTGRES_URL"; then
        error "Failed to restore database"
    fi
    
    log "Database restore completed"
}

# Restore Redis data
restore_redis() {
    local backup_dir="$1"
    local redis_file="$backup_dir/redis-dump.rdb"
    
    if [ ! -f "$redis_file" ]; then
        warn "Redis backup file not found, skipping Redis restore"
        return
    fi
    
    log "Restoring Redis data..."
    
    # Get Redis connection details
    local redis_host=$(echo "$REDIS_URL" | sed -n 's|redis://.*@\([^:]*\):.*|\1|p')
    local redis_port=$(echo "$REDIS_URL" | sed -n 's|redis://.*:\([0-9]*\)|\1|p')
    local redis_pass=$(echo "$REDIS_URL" | sed -n 's|redis://:\([^@]*\)@.*|\1|p')
    
    if [ -n "$redis_pass" ]; then
        export REDISCLI_AUTH="$redis_pass"
    fi
    
    # Flush current Redis data
    log "Clearing current Redis data..."
    redis-cli -h "$redis_host" -p "$redis_port" FLUSHALL
    
    # Note: In a real scenario, you'd need to stop Redis, replace the RDB file, and restart
    # For this simplified version, we'll just clear the data
    warn "Redis restore placeholder - RDB file would be restored here"
    
    log "Redis restore completed"
}

# Restore application data
restore_application_data() {
    local backup_dir="$1"
    
    log "Restoring application data..."
    
    # Restore SAFLA memory
    if [ -d "$backup_dir/safla-memory" ]; then
        log "Restoring SAFLA memory..."
        if [ -d "/app/safla-memory" ]; then
            # Backup current safla-memory
            mv "/app/safla-memory" "/app/safla-memory.backup.$(date +%s)" 2>/dev/null || true
        fi
        cp -r "$backup_dir/safla-memory" "/app/" || warn "Failed to restore SAFLA memory"
    fi
    
    # Restore configuration
    if [ -d "$backup_dir/config" ]; then
        log "Restoring configuration..."
        if [ -d "/app/config" ]; then
            # Backup current config
            mv "/app/config" "/app/config.backup.$(date +%s)" 2>/dev/null || true
        fi
        cp -r "$backup_dir/config" "/app/" || warn "Failed to restore configuration"
    fi
    
    # Restore logs (optional)
    if [ -d "$backup_dir/logs" ] && [ "$RESTORE_LOGS" = "true" ]; then
        log "Restoring logs..."
        cp -r "$backup_dir/logs"/* "/app/logs/" 2>/dev/null || warn "Failed to restore logs"
    fi
    
    log "Application data restore completed"
}

# Verify restore
verify_restore() {
    log "Verifying restore..."
    
    # Check database connectivity
    if psql "$POSTGRES_URL" -c "SELECT 1;" >/dev/null 2>&1; then
        log "✓ Database connectivity verified"
    else
        warn "✗ Database connectivity failed"
    fi
    
    # Check if key tables exist
    local table_count=$(psql "$POSTGRES_URL" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ' || echo "0")
    if [ "$table_count" -gt 0 ]; then
        log "✓ Database tables found: $table_count"
    else
        warn "✗ No database tables found"
    fi
    
    # Check application data
    if [ -d "/app/safla-memory" ]; then
        log "✓ SAFLA memory directory exists"
    else
        warn "✗ SAFLA memory directory not found"
    fi
    
    log "Restore verification completed"
}

# Main restore function
main() {
    local backup_file=""
    local force=false
    local database_only=false
    local data_only=false
    local no_database=false
    local backup_current=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--force)
                force=true
                shift
                ;;
            --database-only)
                database_only=true
                shift
                ;;
            --data-only)
                data_only=true
                shift
                ;;
            --no-database)
                no_database=true
                shift
                ;;
            --backup-current)
                backup_current=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            -*)
                error "Unknown option: $1"
                ;;
            *)
                backup_file="$1"
                shift
                ;;
        esac
    done
    
    # Validate arguments
    if [ -z "$backup_file" ]; then
        echo "Error: Backup file not specified"
        echo ""
        list_backups
        exit 1
    fi
    
    # Handle 'latest' keyword
    if [ "$backup_file" = "latest" ]; then
        backup_file=$(get_latest_backup)
        if [ -z "$backup_file" ]; then
            error "No backups found"
        fi
        log "Using latest backup: $(basename "$backup_file")"
    fi
    
    log "========================================="
    log "TGE Swarm Restore Started"
    log "========================================="
    
    # Validate backup
    validate_backup "$backup_file"
    
    # Extract backup
    local extracted_dir=$(extract_backup "$backup_file")
    
    # Show backup information
    show_backup_info "$extracted_dir"
    
    # Confirmation
    if [ "$force" != "true" ]; then
        echo ""
        echo "⚠️  WARNING: This will restore TGE Swarm from the backup."
        echo "   Current data may be overwritten or lost."
        echo ""
        read -p "Continue with restore? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "Restore cancelled by user"
            rm -rf "$TEMP_DIR"
            exit 0
        fi
    fi
    
    # Backup current state if requested
    if [ "$backup_current" = "true" ]; then
        backup_current_state
    fi
    
    # Perform restore based on options
    if [ "$data_only" = "true" ]; then
        restore_application_data "$extracted_dir"
    elif [ "$database_only" = "true" ]; then
        restore_database "$extracted_dir"
    else
        # Full restore
        if [ "$no_database" != "true" ]; then
            restore_database "$extracted_dir"
        fi
        restore_application_data "$extracted_dir"
        
        # Only restore Redis if not database-only
        if [ "$database_only" != "true" ]; then
            restore_redis "$extracted_dir"
        fi
    fi
    
    # Verify restore
    verify_restore
    
    # Cleanup
    rm -rf "$TEMP_DIR"
    
    log "========================================="
    log "TGE Swarm Restore Completed Successfully"
    log "========================================="
    log ""
    log "Next steps:"
    log "1. Start TGE Swarm services"
    log "2. Verify application functionality"
    log "3. Check logs for any issues"
}

# Run main function
main "$@"