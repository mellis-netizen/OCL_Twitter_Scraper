#!/bin/bash

# AWS EC2 Optimized Deployment Script for Crypto TGE Monitor
# This script provides a one-command deployment for fresh EC2 instances

set -e  # Exit on any error

# Configuration
APP_NAME="crypto-tge-monitor"
APP_DIR="/opt/$APP_NAME"
SERVICE_NAME="crypto-tge-monitor"
LOG_DIR="/var/log/$APP_NAME"
STATE_DIR="/var/lib/$APP_NAME"
BACKUP_DIR="/opt/$APP_NAME/backups"
REPO_URL="https://github.com/mellis-netizen/OCL_Twitter_Scraper.git" 

# AWS-specific configuration
AWS_REGION="us-east-1"  # Default region, can be overridden
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null || echo "unknown")
AVAILABILITY_ZONE=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone 2>/dev/null || echo "unknown")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Enhanced logging with timestamps and EC2 context
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] [EC2:$INSTANCE_ID] $1${NC}"
    logger -t crypto-tge-deploy "$1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] [EC2:$INSTANCE_ID] WARNING: $1${NC}"
    logger -t crypto-tge-deploy -p user.warning "$1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] [EC2:$INSTANCE_ID] ERROR: $1${NC}"
    logger -t crypto-tge-deploy -p user.error "$1"
    exit 1
}

info() {
    echo -e "${CYAN}[$(date +'%Y-%m-%d %H:%M:%S')] [EC2:$INSTANCE_ID] INFO: $1${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root. Use: sudo ./ec2-deploy.sh"
    fi
}

# Detect EC2 instance type and optimize accordingly
detect_instance_type() {
    INSTANCE_TYPE=$(curl -s http://169.254.169.254/latest/meta-data/instance-type 2>/dev/null || echo "unknown")
    info "Detected EC2 instance type: $INSTANCE_TYPE"
    info "Availability Zone: $AVAILABILITY_ZONE"
    
    # Optimize based on instance type
    case $INSTANCE_TYPE in
        t2.micro|t3.micro|t3a.micro)
            warn "Micro instance detected - enabling memory optimizations"
            export OPTIMIZE_FOR_MICRO=1
            ;;
        t2.small|t3.small|t3a.small)
            info "Small instance detected - standard configuration"
            ;;
        *)
            info "Standard or larger instance detected - full features enabled"
            ;;
    esac
}

# Install AWS CloudWatch agent and configure logging
setup_cloudwatch() {
    log "Setting up AWS CloudWatch logging..."
    
    # Install CloudWatch agent
    wget -q https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
    dpkg -i amazon-cloudwatch-agent.deb || apt-get install -f -y
    rm amazon-cloudwatch-agent.deb
    
    # Create CloudWatch configuration
    cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << EOF
{
    "agent": {
        "metrics_collection_interval": 300,
        "run_as_user": "root"
    },
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "$LOG_DIR/crypto_monitor.log",
                        "log_group_name": "/aws/ec2/crypto-tge-monitor",
                        "log_stream_name": "{instance_id}/application",
                        "timestamp_format": "%Y-%m-%d %H:%M:%S"
                    },
                    {
                        "file_path": "/var/log/syslog",
                        "log_group_name": "/aws/ec2/crypto-tge-monitor",
                        "log_stream_name": "{instance_id}/syslog"
                    }
                ]
            }
        }
    },
    "metrics": {
        "namespace": "CryptoTGEMonitor",
        "metrics_collected": {
            "cpu": {
                "measurement": [
                    "cpu_usage_idle",
                    "cpu_usage_iowait",
                    "cpu_usage_user",
                    "cpu_usage_system"
                ],
                "metrics_collection_interval": 300
            },
            "disk": {
                "measurement": [
                    "used_percent"
                ],
                "metrics_collection_interval": 300,
                "resources": [
                    "*"
                ]
            },
            "diskio": {
                "measurement": [
                    "io_time"
                ],
                "metrics_collection_interval": 300,
                "resources": [
                    "*"
                ]
            },
            "mem": {
                "measurement": [
                    "mem_used_percent"
                ],
                "metrics_collection_interval": 300
            }
        }
    }
}
EOF

    # Start CloudWatch agent
    systemctl enable amazon-cloudwatch-agent
    systemctl start amazon-cloudwatch-agent
    
    log "CloudWatch logging configured successfully"
}

# Install system dependencies optimized for Ubuntu/Amazon Linux
install_system_deps() {
    log "Installing system dependencies optimized for EC2..."

    # Detect OS
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
    fi

    case $OS in
        "Ubuntu"*)
            apt-get update -q
            apt-get install -y \
                python3 python3-pip python3-venv \
                git curl wget unzip \
                supervisor nginx \
                awscli \
                htop iotop \
                logrotate rsyslog \
                fail2ban ufw
            ;;
        "Amazon Linux"*)
            yum update -y
            yum install -y \
                python3 python3-pip \
                git curl wget unzip \
                supervisor nginx \
                awscli \
                htop iotop \
                logrotate rsyslog
            amazon-linux-extras install -y python3.8
            ;;
        *)
            warn "Unknown OS detected, attempting Ubuntu-style installation"
            apt-get update -q
            apt-get install -y python3 python3-pip python3-venv git curl wget unzip supervisor
            ;;
    esac

    # Install Docker for potential future containerization
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    usermod -aG docker ubuntu 2>/dev/null || true  # Add ubuntu user to docker group
    rm get-docker.sh

    log "System dependencies installed successfully"
}

# Setup security hardening for EC2
setup_security() {
    log "Setting up EC2 security hardening..."
    
    # Configure UFW firewall
    ufw --force reset
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow ssh
    ufw allow 80   # HTTP for health checks
    ufw allow 443  # HTTPS for health checks
    ufw --force enable
    
    # Configure fail2ban
    cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
logpath = %(sshd_log)s
backend = %(sshd_backend)s
EOF
    
    systemctl enable fail2ban
    systemctl start fail2ban
    
    # Set up automatic security updates
    if command -v unattended-upgrades &> /dev/null; then
        dpkg-reconfigure -plow unattended-upgrades
    fi
    
    log "Security hardening completed"
}

# Create application user with proper EC2 permissions
create_app_user() {
    log "Creating application user with EC2 optimizations..."

    if ! id "$APP_NAME" &>/dev/null; then
        useradd --system --shell /bin/bash --home-dir $APP_DIR --create-home $APP_NAME
        
        # Add to necessary groups for EC2 operations
        usermod -aG systemd-journal $APP_NAME
        usermod -aG adm $APP_NAME  # For log access
        
        log "Created user: $APP_NAME"
    else
        log "User $APP_NAME already exists"
    fi
}

# Create directories with EC2-optimized structure
create_directories() {
    log "Creating EC2-optimized directory structure..."

    # Create all necessary directories
    mkdir -p $APP_DIR/{current,releases,shared} $LOG_DIR $STATE_DIR $BACKUP_DIR
    mkdir -p $APP_DIR/shared/{logs,state,config}
    
    # Create symlinks for shared resources
    ln -sf $APP_DIR/shared/state $APP_DIR/current/state 2>/dev/null || true
    ln -sf $APP_DIR/shared/logs $APP_DIR/current/logs 2>/dev/null || true
    
    # Set proper ownership and permissions
    chown -R $APP_NAME:$APP_NAME $APP_DIR $LOG_DIR $STATE_DIR $BACKUP_DIR
    chmod 755 $APP_DIR $LOG_DIR
    chmod 750 $STATE_DIR $BACKUP_DIR
    chmod 700 $APP_DIR/shared/config  # Secure config directory
    
    log "Directory structure created successfully"
}

# Deploy code with Git (production-ready approach)
deploy_code() {
    log "Deploying application code from Git..."

    # Generate release name
    RELEASE_NAME="release-$(date +%Y%m%d_%H%M%S)"
    RELEASE_DIR="$APP_DIR/releases/$RELEASE_NAME"
    
    # Stop service if running
    if systemctl is-active --quiet $SERVICE_NAME; then
        log "Stopping $SERVICE_NAME service..."
        systemctl stop $SERVICE_NAME
    fi
    
    # Create release directory
    mkdir -p $RELEASE_DIR
    
    # Clone or copy code
    if [ -n "$REPO_URL" ] && [ "$REPO_URL" != "https://github.com/YOUR_USERNAME/crypto-tge-monitor.git" ]; then
        log "Cloning from repository: $REPO_URL"
        git clone $REPO_URL $RELEASE_DIR
        cd $RELEASE_DIR
        git checkout main 2>/dev/null || git checkout master 2>/dev/null || true
    else
        # Copy from current directory (if deploying from local files)
        log "Copying application files from current directory..."
        cp -r . $RELEASE_DIR/
        # Remove unnecessary files
        rm -rf $RELEASE_DIR/.git $RELEASE_DIR/logs $RELEASE_DIR/state 2>/dev/null || true
    fi
    
    # Create symlinks to shared resources
    cd $RELEASE_DIR
    rm -rf logs state 2>/dev/null || true
    ln -sf $APP_DIR/shared/logs logs
    ln -sf $APP_DIR/shared/state state
    
    # Update current symlink atomically
    ln -sfn $RELEASE_DIR $APP_DIR/current.tmp
    mv $APP_DIR/current.tmp $APP_DIR/current
    
    # Set ownership
    chown -R $APP_NAME:$APP_NAME $RELEASE_DIR
    
    # Keep only last 5 releases
    cd $APP_DIR/releases
    ls -t | tail -n +6 | xargs rm -rf 2>/dev/null || true
    
    log "Application code deployed successfully to $RELEASE_NAME"
}

# Setup Python environment with EC2 optimizations
setup_virtualenv() {
    log "Setting up optimized Python virtual environment..."

    # Remove old venv if exists
    rm -rf $APP_DIR/venv
    
    # Create new virtual environment
    sudo -u $APP_NAME python3 -m venv $APP_DIR/venv
    
    # Upgrade pip and install wheel
    sudo -u $APP_NAME $APP_DIR/venv/bin/pip install --upgrade pip wheel setuptools
    
    # Install dependencies with optimizations for micro instances
    if [ "$OPTIMIZE_FOR_MICRO" = "1" ]; then
        # Install one package at a time to avoid memory issues
        while IFS= read -r line; do
            if [[ $line =~ ^[^#]*= ]]; then
                sudo -u $APP_NAME $APP_DIR/venv/bin/pip install --no-cache-dir "$line"
            fi
        done < $APP_DIR/current/requirements.txt
    else
        sudo -u $APP_NAME $APP_DIR/venv/bin/pip install -r $APP_DIR/current/requirements.txt
    fi
    
    log "Virtual environment setup complete"
}

# Create optimized systemd service for EC2
create_service() {
    log "Creating optimized systemd service for EC2..."

    cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=Crypto TGE Monitor - AWS EC2 Optimized
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=$APP_NAME
Group=$APP_NAME
WorkingDirectory=$APP_DIR/current
Environment=PYTHONPATH=$APP_DIR/current
Environment=AWS_DEFAULT_REGION=$AWS_REGION
Environment=EC2_INSTANCE_ID=$INSTANCE_ID
Environment=EC2_AVAILABILITY_ZONE=$AVAILABILITY_ZONE
ExecStart=$APP_DIR/venv/bin/python src/main.py --mode continuous
ExecReload=/bin/kill -HUP \$MAINPID

# Restart configuration
Restart=always
RestartSec=10
StartLimitBurst=5

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$LOG_DIR $STATE_DIR $BACKUP_DIR $APP_DIR/shared

# Resource limits for EC2
MemoryMax=512M
CPUQuota=80%

# Environment file
EnvironmentFile=-$APP_DIR/.env

# Health check
ExecStartPost=/bin/sleep 30
ExecStartPost=/opt/crypto-tge-monitor/scripts/health-check.sh

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable $SERVICE_NAME
    
    log "Systemd service created and enabled"
}

# Setup NGINX reverse proxy for health checks
setup_nginx() {
    log "Setting up NGINX for health checks..."
    
    cat > /etc/nginx/sites-available/$APP_NAME << EOF
server {
    listen 80;
    server_name _;
    
    location /health {
        access_log off;
        return 200 "healthy\\n";
        add_header Content-Type text/plain;
    }
    
    location /status {
        access_log off;
        proxy_pass http://127.0.0.1:8080/status;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
    
    location / {
        return 404;
    }
}
EOF

    # Enable site
    ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    # Test and reload NGINX
    nginx -t && systemctl reload nginx
    systemctl enable nginx
    
    log "NGINX configured for health checks"
}

# Create health check script
create_health_check() {
    log "Creating health check scripts..."
    
    mkdir -p $APP_DIR/scripts
    
    cat > $APP_DIR/scripts/health-check.sh << 'EOF'
#!/bin/bash

SERVICE_NAME="crypto-tge-monitor"
APP_DIR="/opt/crypto-tge-monitor"
LOG_FILE="/var/log/crypto-tge-monitor/crypto_monitor.log"

# Check if service is running
if ! systemctl is-active --quiet $SERVICE_NAME; then
    echo "CRITICAL: Service is not running"
    exit 2
fi

# Check if log file exists and has recent entries
if [ -f "$LOG_FILE" ]; then
    LAST_LOG=$(stat -c %Y "$LOG_FILE" 2>/dev/null || echo 0)
    CURRENT_TIME=$(date +%s)
    TIME_DIFF=$((CURRENT_TIME - LAST_LOG))
    
    if [ $TIME_DIFF -gt 3600 ]; then  # 1 hour
        echo "WARNING: No recent log activity"
        exit 1
    fi
fi

# Check memory usage
MEMORY_USAGE=$(ps -o pid,ppid,cmd,%mem --sort=-%mem -p $(pgrep -f "crypto-tge-monitor") | tail -n +2 | awk '{print $4}' | head -1)
if [ -n "$MEMORY_USAGE" ] && [ $(echo "$MEMORY_USAGE > 50" | bc -l 2>/dev/null || echo 0) -eq 1 ]; then
    echo "WARNING: High memory usage: ${MEMORY_USAGE}%"
fi

echo "OK: Service is healthy"
exit 0
EOF

    chmod +x $APP_DIR/scripts/health-check.sh
    chown $APP_NAME:$APP_NAME $APP_DIR/scripts/health-check.sh
    
    # Create monitoring script
    cat > $APP_DIR/scripts/monitor.sh << 'EOF'
#!/bin/bash

# Simple monitoring script for cron
SERVICE_NAME="crypto-tge-monitor"

if ! systemctl is-active --quiet $SERVICE_NAME; then
    echo "$(date): Service $SERVICE_NAME is down, restarting..." | logger
    systemctl start $SERVICE_NAME
    
    # Send notification (if SNS topic is configured)
    if [ -n "$SNS_TOPIC_ARN" ]; then
        aws sns publish --topic-arn "$SNS_TOPIC_ARN" \
            --message "Crypto TGE Monitor service restarted on $(hostname)" \
            --subject "Service Alert" 2>/dev/null || true
    fi
fi
EOF

    chmod +x $APP_DIR/scripts/monitor.sh
    
    # Add to crontab
    echo "*/5 * * * * $APP_DIR/scripts/monitor.sh" | crontab -u root -
    
    log "Health check scripts created"
}

# Setup automated backups (S3 optional)
setup_backups() {
    log "Setting up automated backups..."
    
    cat > $APP_DIR/scripts/backup.sh << 'EOF'
#!/bin/bash

APP_NAME="crypto-tge-monitor"
STATE_DIR="/var/lib/$APP_NAME"
BACKUP_DIR="/opt/$APP_NAME/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create local backup
tar -czf $BACKUP_DIR/state_backup_$DATE.tar.gz -C $STATE_DIR .

# Keep only last 7 days of local backups
find $BACKUP_DIR -name "state_backup_*.tar.gz" -mtime +7 -delete

# Upload to S3 only if bucket is configured and AWS CLI is available
if [ -n "$S3_BACKUP_BUCKET" ] && command -v aws &> /dev/null; then
    log "Uploading backup to S3 bucket: $S3_BACKUP_BUCKET"
    if aws s3 cp $BACKUP_DIR/state_backup_$DATE.tar.gz \
        s3://$S3_BACKUP_BUCKET/crypto-tge-monitor/$(hostname)/ 2>/dev/null; then
        log "S3 backup successful"
    else
        log "S3 backup failed - continuing with local backup only"
    fi
else
    log "S3 backup not configured - keeping local backup only"
fi

echo "Backup completed: state_backup_$DATE.tar.gz"
EOF

    chmod +x $APP_DIR/scripts/backup.sh
    chown $APP_NAME:$APP_NAME $APP_DIR/scripts/backup.sh
    
    # Add daily backup to crontab
    echo "0 2 * * * $APP_DIR/scripts/backup.sh" | crontab -u root -
    
    log "Automated backups configured (S3 optional)"
}

# Create environment configuration with AWS integration
setup_env_config() {
    log "Setting up environment configuration..."

    if [ ! -f "$APP_DIR/.env" ]; then
        cat > $APP_DIR/.env << EOF
# Email Configuration (Required)
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
RECIPIENT_EMAIL=recipient@example.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Twitter API Configuration (Optional)
TWITTER_BEARER_TOKEN=your-bearer-token

# AWS Configuration
AWS_DEFAULT_REGION=$AWS_REGION
EC2_INSTANCE_ID=$INSTANCE_ID
EC2_AVAILABILITY_ZONE=$AVAILABILITY_ZONE

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=$LOG_DIR/crypto_monitor.log

# System Configuration
DISABLE_TWITTER=0
TWITTER_ENABLE_SEARCH=1

# Optional: S3 backup bucket
# S3_BACKUP_BUCKET=your-backup-bucket

# Optional: SNS topic for alerts
# SNS_TOPIC_ARN=arn:aws:sns:region:account:topic-name
EOF

        chown $APP_NAME:$APP_NAME $APP_DIR/.env
        chmod 600 $APP_DIR/.env
        
        warn "Environment file created at $APP_DIR/.env - PLEASE UPDATE WITH YOUR CREDENTIALS"
    else
        log "Environment file already exists"
    fi
}

# Setup log rotation optimized for EC2
setup_logrotate() {
    log "Setting up log rotation for EC2..."

    cat > /etc/logrotate.d/$APP_NAME << EOF
$LOG_DIR/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 644 $APP_NAME $APP_NAME
    copytruncate
    postrotate
        # Send SIGUSR1 to application for log rotation
        systemctl reload $SERVICE_NAME > /dev/null 2>&1 || true
        
        # Sync old logs to S3 only if configured and AWS CLI is available
        if [ -n "\$S3_BACKUP_BUCKET" ] && command -v aws &> /dev/null; then
            find $LOG_DIR -name "*.gz" -mtime +1 -exec aws s3 cp {} s3://\$S3_BACKUP_BUCKET/crypto-tge-monitor/$(hostname)/logs/ \; -delete 2>/dev/null || true
        fi
    endscript
}
EOF

    log "Log rotation configured"
}

# Start all services
start_services() {
    log "Starting all services..."

    # Start in order
    systemctl start nginx
    systemctl start $SERVICE_NAME
    
    # Wait a moment for services to start
    sleep 5
    
    # Check status
    systemctl status nginx --no-pager -l | head -10
    systemctl status $SERVICE_NAME --no-pager -l | head -10
    
    log "All services started successfully"
}

# Main deployment function
main() {
    log "Starting AWS EC2 optimized deployment of Crypto TGE Monitor..."
    
    info "Instance: $INSTANCE_TYPE in $AVAILABILITY_ZONE"
    
    check_root
    detect_instance_type
    install_system_deps
    setup_security
    setup_cloudwatch
    create_app_user
    create_directories
    deploy_code
    setup_virtualenv
    create_service
    setup_nginx
    create_health_check
    setup_backups
    setup_env_config
    setup_logrotate
    start_services
    
    log "EC2 deployment completed successfully!"
    echo
    echo -e "${BLUE}=== DEPLOYMENT SUMMARY ===${NC}"
    echo -e "${GREEN}Instance Type:${NC} $INSTANCE_TYPE"
    echo -e "${GREEN}Instance ID:${NC} $INSTANCE_ID"
    echo -e "${GREEN}Availability Zone:${NC} $AVAILABILITY_ZONE"
    echo -e "${GREEN}Application Directory:${NC} $APP_DIR"
    echo -e "${GREEN}Service Name:${NC} $SERVICE_NAME"
    echo
    echo -e "${BLUE}=== NEXT STEPS ===${NC}"
    echo "1. Configure your credentials:"
    echo "   sudo nano $APP_DIR/.env"
    echo
    echo "2. Restart the service:"
    echo "   sudo systemctl restart $SERVICE_NAME"
    echo
    echo "3. Monitor the service:"
    echo "   sudo systemctl status $SERVICE_NAME"
    echo "   sudo journalctl -u $SERVICE_NAME -f"
    echo
    echo "4. Check health endpoint:"
    echo "   curl http://localhost/health"
    echo
    echo "5. View CloudWatch logs:"
    echo "   AWS Console -> CloudWatch -> Log Groups -> /aws/ec2/crypto-tge-monitor"
    echo
    echo -e "${GREEN}Service is configured to start automatically on boot.${NC}"
    echo -e "${GREEN}Automated monitoring and backups are enabled.${NC}"
}

# Handle script arguments
case ${1:-deploy} in
    deploy)
        main
        ;;
    health)
        $APP_DIR/scripts/health-check.sh
        ;;
    backup)
        $APP_DIR/scripts/backup.sh
        ;;
    *)
        echo "Usage: $0 [deploy|health|backup]"
        exit 1
        ;;
esac