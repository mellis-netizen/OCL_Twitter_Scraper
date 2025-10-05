#!/bin/bash

# ===============================================================================
# Enhanced TGE Monitor System - Automated EC2 Deployment Script
# ===============================================================================
# 
# This script automatically deploys the Enhanced TGE Monitor System on a fresh
# Ubuntu 22.04 EC2 instance. Run this script on your EC2 instance after initial
# SSH connection.
#
# Usage: ./deploy-ec2-automated.sh
# 
# Prerequisites:
# - Fresh Ubuntu 22.04 EC2 instance
# - SSH access to the instance
# - Internet connectivity
# ===============================================================================

set -e  # Exit on any error
set -u  # Exit on undefined variables

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration variables
APP_USER="tgemonitor"
APP_DIR="/opt/tge-monitor"
VENV_DIR="$APP_DIR/venv"
LOG_FILE="/tmp/tge-monitor-deployment.log"
POSTGRES_VERSION="15"
PYTHON_VERSION="3.11"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if service is running
service_running() {
    systemctl is-active --quiet "$1"
}

# Function to wait for user input
confirm() {
    local prompt="$1"
    local response
    echo -n "$prompt (y/N): "
    read -r response
    case "$response" in
        [yY][eE][sS]|[yY]) 
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Function to generate secure password
generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-25
}

# Function to create systemd service
create_systemd_service() {
    local service_name="$1"
    local service_description="$2"
    local exec_start="$3"
    local service_file="/etc/systemd/system/${service_name}.service"
    
    print_status "Creating systemd service: $service_name"
    
    sudo tee "$service_file" > /dev/null <<EOF
[Unit]
Description=$service_description
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$exec_start
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable "$service_name"
    print_success "Created and enabled $service_name service"
}

# Function to setup environment file
setup_environment() {
    print_status "Setting up environment configuration..."
    
    # Generate secure passwords
    local db_password=$(generate_password)
    local secret_key=$(generate_password)$(generate_password)
    local admin_password=$(generate_password)
    
    # Create .env file
    sudo -u "$APP_USER" tee "$APP_DIR/.env" > /dev/null <<EOF
# Database Configuration
DATABASE_URL=postgresql://$APP_USER:$db_password@localhost:5432/tge_monitor
REDIS_URL=redis://localhost:6379/0

# Security Configuration
SECRET_KEY=$secret_key
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@tgemonitor.local
ADMIN_PASSWORD=$admin_password

# API Configuration
API_PORT=8000
LOG_LEVEL=INFO
ENVIRONMENT=production
WORKERS=4

# Email Configuration (CONFIGURE THESE MANUALLY)
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
EMAIL_USER=your_email@domain.com
EMAIL_PASSWORD=your_email_password
RECIPIENT_EMAIL=alerts@yourdomain.com

# Twitter API Configuration (OPTIONAL)
TWITTER_BEARER_TOKEN=your_twitter_bearer_token

# Monitoring Configuration
HEALTH_CHECK_INTERVAL=60
BACKUP_RETENTION_DAYS=7
EOF

    # Store credentials securely
    sudo -u "$APP_USER" tee "$APP_DIR/DEPLOYMENT_CREDENTIALS.txt" > /dev/null <<EOF
=== TGE Monitor Deployment Credentials ===
Generated on: $(date)

Database Password: $db_password
Admin Password: $admin_password
Secret Key: $secret_key

IMPORTANT: 
1. Configure email settings in .env file
2. Add Twitter API credentials if needed
3. Keep this file secure and backed up
4. Delete this file after noting credentials
EOF

    print_success "Environment file created with secure credentials"
    print_warning "IMPORTANT: Check $APP_DIR/DEPLOYMENT_CREDENTIALS.txt for generated passwords"
    
    # Return the database password for use in PostgreSQL setup
    echo "$db_password"
}

# Function to install system dependencies
install_system_dependencies() {
    print_status "Installing system dependencies..."
    
    # Update package lists
    sudo apt update >> "$LOG_FILE" 2>&1
    
    # Install essential packages
    sudo apt install -y \
        curl \
        wget \
        git \
        vim \
        htop \
        build-essential \
        software-properties-common \
        ca-certificates \
        gnupg \
        lsb-release \
        ufw \
        fail2ban \
        logrotate \
        cron >> "$LOG_FILE" 2>&1
    
    print_success "System dependencies installed"
}

# Function to install Python
install_python() {
    print_status "Installing Python $PYTHON_VERSION..."
    
    # Add Python PPA
    sudo add-apt-repository ppa:deadsnakes/ppa -y >> "$LOG_FILE" 2>&1
    sudo apt update >> "$LOG_FILE" 2>&1
    
    # Install Python and dependencies
    sudo apt install -y \
        python$PYTHON_VERSION \
        python$PYTHON_VERSION-venv \
        python$PYTHON_VERSION-dev \
        python3-pip \
        libpq-dev \
        gcc \
        libssl-dev \
        libffi-dev \
        libxml2-dev \
        libxslt1-dev \
        zlib1g-dev >> "$LOG_FILE" 2>&1
    
    # Verify installation
    if python$PYTHON_VERSION --version >> "$LOG_FILE" 2>&1; then
        print_success "Python $PYTHON_VERSION installed successfully"
    else
        print_error "Failed to install Python $PYTHON_VERSION"
        exit 1
    fi
}

# Function to install PostgreSQL
install_postgresql() {
    print_status "Installing PostgreSQL $POSTGRES_VERSION..."
    
    # Add PostgreSQL official repository
    sudo sh -c 'echo "deb https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add - >> "$LOG_FILE" 2>&1
    sudo apt update >> "$LOG_FILE" 2>&1
    
    # Install PostgreSQL
    sudo apt install -y postgresql-$POSTGRES_VERSION postgresql-client-$POSTGRES_VERSION postgresql-contrib-$POSTGRES_VERSION >> "$LOG_FILE" 2>&1
    
    # Start and enable PostgreSQL
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
    
    if service_running postgresql; then
        print_success "PostgreSQL installed and started"
    else
        print_error "Failed to start PostgreSQL"
        exit 1
    fi
}

# Function to setup PostgreSQL database
setup_postgresql() {
    local db_password="$1"
    print_status "Setting up PostgreSQL database..."
    
    # Create database user and database
    sudo -u postgres psql << EOF >> "$LOG_FILE" 2>&1
CREATE USER $APP_USER WITH PASSWORD '$db_password';
CREATE DATABASE tge_monitor OWNER $APP_USER;
GRANT ALL PRIVILEGES ON DATABASE tge_monitor TO $APP_USER;
\q
EOF
    
    # Configure PostgreSQL for local connections
    local pg_version=$(sudo -u postgres psql -t -c "SELECT version();" | grep -oP '\d+\.\d+' | head -1 | cut -d. -f1)
    local pg_config_dir="/etc/postgresql/$pg_version/main"
    
    # Backup original configs
    sudo cp "$pg_config_dir/pg_hba.conf" "$pg_config_dir/pg_hba.conf.backup"
    
    # Add authentication for app user
    echo "local   all             $APP_USER                              md5" | sudo tee -a "$pg_config_dir/pg_hba.conf" > /dev/null
    echo "host    all             $APP_USER      127.0.0.1/32            md5" | sudo tee -a "$pg_config_dir/pg_hba.conf" > /dev/null
    
    # Restart PostgreSQL
    sudo systemctl restart postgresql
    
    # Test connection
    if sudo -u "$APP_USER" PGPASSWORD="$db_password" psql -h localhost -U "$APP_USER" -d tge_monitor -c "SELECT 1;" >> "$LOG_FILE" 2>&1; then
        print_success "PostgreSQL database setup completed"
    else
        print_error "Failed to setup PostgreSQL database"
        exit 1
    fi
}

# Function to install Redis
install_redis() {
    print_status "Installing and configuring Redis..."
    
    # Install Redis
    sudo apt install -y redis-server >> "$LOG_FILE" 2>&1
    
    # Configure Redis for production
    sudo sed -i 's/supervised no/supervised systemd/g' /etc/redis/redis.conf
    sudo sed -i 's/# maxmemory <bytes>/maxmemory 256mb/g' /etc/redis/redis.conf
    sudo sed -i 's/# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/g' /etc/redis/redis.conf
    
    # Restart and enable Redis
    sudo systemctl restart redis-server
    sudo systemctl enable redis-server
    
    # Test Redis
    if redis-cli ping >> "$LOG_FILE" 2>&1; then
        print_success "Redis installed and configured"
    else
        print_error "Failed to install Redis"
        exit 1
    fi
}

# Function to install Nginx
install_nginx() {
    print_status "Installing and configuring Nginx..."
    
    # Install Nginx
    sudo apt install -y nginx >> "$LOG_FILE" 2>&1
    
    # Create Nginx configuration
    sudo tee /etc/nginx/sites-available/tge-monitor > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-XSS-Protection "1; mode=block";
    add_header X-Content-Type-Options "nosniff";

    # Main application
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeouts
        proxy_connect_timeout       60s;
        proxy_send_timeout          60s;
        proxy_read_timeout          60s;
    }

    # WebSocket support
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://localhost:8000/health;
        access_log off;
    }
}
EOF

    # Enable site
    sudo ln -sf /etc/nginx/sites-available/tge-monitor /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Test configuration
    if sudo nginx -t >> "$LOG_FILE" 2>&1; then
        sudo systemctl restart nginx
        sudo systemctl enable nginx
        print_success "Nginx installed and configured"
    else
        print_error "Nginx configuration test failed"
        exit 1
    fi
}

# Function to create application user and directories
setup_application_user() {
    print_status "Creating application user and directories..."
    
    # Create user
    if ! id "$APP_USER" &>/dev/null; then
        sudo useradd -m -s /bin/bash "$APP_USER"
        print_success "Created user: $APP_USER"
    else
        print_warning "User $APP_USER already exists"
    fi
    
    # Create application directory
    sudo mkdir -p "$APP_DIR"
    sudo chown "$APP_USER:$APP_USER" "$APP_DIR"
    
    # Create subdirectories
    sudo -u "$APP_USER" mkdir -p "$APP_DIR"/{logs,state,reports,backups}
    
    print_success "Application directories created"
}

# Function to clone repository
clone_repository() {
    print_status "Cloning repository..."
    
    # Check if repository is already cloned
    if [ -d "$APP_DIR/.git" ]; then
        print_warning "Repository already exists, pulling latest changes..."
        sudo -u "$APP_USER" git -C "$APP_DIR" pull >> "$LOG_FILE" 2>&1
    else
        # For this example, we'll create the necessary files since we can't clone from GitHub directly
        print_status "Setting up application files..."
        
        # Copy current directory to app directory (modify this for your actual repository)
        if [ -f "requirements.txt" ]; then
            sudo cp -r . "$APP_DIR/"
            sudo chown -R "$APP_USER:$APP_USER" "$APP_DIR"
            print_success "Application files copied"
        else
            print_error "This script should be run from the TGE Monitor repository directory"
            print_error "Please clone the repository first and run this script from within it"
            exit 1
        fi
    fi
}

# Function to setup Python virtual environment
setup_python_environment() {
    print_status "Setting up Python virtual environment..."
    
    # Create virtual environment
    sudo -u "$APP_USER" python$PYTHON_VERSION -m venv "$VENV_DIR"
    
    # Upgrade pip
    sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install --upgrade pip >> "$LOG_FILE" 2>&1
    
    # Install requirements
    if [ -f "$APP_DIR/requirements.txt" ]; then
        print_status "Installing Python dependencies..."
        sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt" >> "$LOG_FILE" 2>&1
        
        # Install additional production dependencies
        sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install gunicorn supervisor >> "$LOG_FILE" 2>&1
        
        print_success "Python dependencies installed"
    else
        print_error "requirements.txt not found in $APP_DIR"
        exit 1
    fi
    
    # Fix NLTK SSL issue
    sudo -u "$APP_USER" "$VENV_DIR/bin/python" -c "
import ssl
import nltk
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context
nltk.download('punkt')
" >> "$LOG_FILE" 2>&1 || print_warning "NLTK download failed (will try later)"
}

# Function to initialize database
initialize_database() {
    print_status "Initializing application database..."
    
    # Initialize database schema
    sudo -u "$APP_USER" bash -c "
        cd '$APP_DIR'
        source '$VENV_DIR/bin/activate'
        python -c \"
from src.database import init_db
from src.auth import create_admin_user_if_not_exists
from src.database import DatabaseManager

print('Initializing database...')
init_db()
print('Database tables created')

with DatabaseManager.get_session() as db:
    create_admin_user_if_not_exists(db)
print('Admin user created')
\"
    " >> "$LOG_FILE" 2>&1
    
    if [ $? -eq 0 ]; then
        print_success "Database initialized successfully"
    else
        print_error "Failed to initialize database"
        exit 1
    fi
}

# Function to setup systemd services
setup_services() {
    print_status "Setting up systemd services..."
    
    # Create API service
    create_systemd_service \
        "tge-monitor-api" \
        "TGE Monitor API Server" \
        "$VENV_DIR/bin/python $APP_DIR/run_enhanced_system.py --mode server"
    
    # Create worker service
    create_systemd_service \
        "tge-monitor-worker" \
        "TGE Monitor Background Worker" \
        "$VENV_DIR/bin/python -m src.main --mode continuous"
    
    print_success "Systemd services created"
}

# Function to setup monitoring and maintenance
setup_monitoring() {
    print_status "Setting up monitoring and maintenance..."
    
    # Create health check script
    sudo tee "$APP_DIR/health_check.sh" > /dev/null <<'EOF'
#!/bin/bash
LOG_FILE="/opt/tge-monitor/logs/health_check.log"
date >> "$LOG_FILE"

# Check API health
API_HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null | grep -c "healthy" || echo "0")

# Check services
API_STATUS=$(systemctl is-active tge-monitor-api 2>/dev/null || echo "inactive")
WORKER_STATUS=$(systemctl is-active tge-monitor-worker 2>/dev/null || echo "inactive")

# Check database
DB_CHECK=$(sudo -u postgres psql -t -c "SELECT 1" 2>/dev/null | grep -c "1" || echo "0")

# Check Redis
REDIS_CHECK=$(redis-cli ping 2>/dev/null | grep -c "PONG" || echo "0")

if [ "$API_HEALTH" -eq 1 ] && [ "$API_STATUS" = "active" ] && [ "$WORKER_STATUS" = "active" ] && [ "$DB_CHECK" -eq 1 ] && [ "$REDIS_CHECK" -eq 1 ]; then
    echo "✅ All systems operational" >> "$LOG_FILE"
    exit 0
else
    echo "❌ System health check failed" >> "$LOG_FILE"
    echo "API: $API_HEALTH, API_SVC: $API_STATUS, Worker: $WORKER_STATUS, DB: $DB_CHECK, Redis: $REDIS_CHECK" >> "$LOG_FILE"
    
    # Attempt to restart services if they're down
    if [ "$API_STATUS" != "active" ]; then
        systemctl restart tge-monitor-api
        echo "Restarted API service" >> "$LOG_FILE"
    fi
    
    if [ "$WORKER_STATUS" != "active" ]; then
        systemctl restart tge-monitor-worker
        echo "Restarted worker service" >> "$LOG_FILE"
    fi
    
    exit 1
fi
EOF

    sudo chmod +x "$APP_DIR/health_check.sh"
    
    # Create backup script
    sudo tee "$APP_DIR/backup.sh" > /dev/null <<EOF
#!/bin/bash
BACKUP_DIR="$APP_DIR/backups"
DATE=\$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "\$BACKUP_DIR"

# Backup database
sudo -u postgres pg_dump tge_monitor | gzip > "\$BACKUP_DIR/db_backup_\$DATE.sql.gz"

# Backup application state
tar -czf "\$BACKUP_DIR/state_backup_\$DATE.tar.gz" $APP_DIR/state/ 2>/dev/null || true

# Keep only last 7 days of backups
find "\$BACKUP_DIR" -type f -mtime +7 -delete 2>/dev/null || true

echo "Backup completed: \$DATE" >> $APP_DIR/logs/backup.log
EOF

    sudo chmod +x "$APP_DIR/backup.sh"
    
    # Setup log rotation
    sudo tee /etc/logrotate.d/tge-monitor > /dev/null <<EOF
$APP_DIR/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 $APP_USER $APP_USER
    sharedscripts
    postrotate
        systemctl reload tge-monitor-api > /dev/null 2>&1 || true
        systemctl reload tge-monitor-worker > /dev/null 2>&1 || true
    endscript
}
EOF

    # Setup cron jobs
    sudo -u "$APP_USER" crontab -l 2>/dev/null | {
        cat
        echo "*/5 * * * * $APP_DIR/health_check.sh"
        echo "0 2 * * * $APP_DIR/backup.sh"
    } | sudo -u "$APP_USER" crontab -
    
    print_success "Monitoring and maintenance setup completed"
}

# Function to configure firewall
configure_firewall() {
    print_status "Configuring firewall..."
    
    # Configure UFW
    sudo ufw --force reset >> "$LOG_FILE" 2>&1
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw allow ssh
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    
    # Enable firewall
    sudo ufw --force enable >> "$LOG_FILE" 2>&1
    
    # Configure fail2ban
    sudo systemctl enable fail2ban
    sudo systemctl start fail2ban
    
    print_success "Firewall configured"
}

# Function to start services
start_services() {
    print_status "Starting services..."
    
    # Start and test services
    sudo systemctl start tge-monitor-api
    sudo systemctl start tge-monitor-worker
    
    # Wait a moment for services to start
    sleep 5
    
    # Check service status
    if service_running tge-monitor-api && service_running tge-monitor-worker; then
        print_success "All services started successfully"
    else
        print_warning "Some services may not have started properly"
        print_status "Checking service status..."
        sudo systemctl status tge-monitor-api --no-pager -l
        sudo systemctl status tge-monitor-worker --no-pager -l
    fi
}

# Function to run system tests
run_tests() {
    print_status "Running system tests..."
    
    # Test API endpoint
    if curl -s http://localhost:8000/health > /dev/null; then
        print_success "API health check passed"
    else
        print_warning "API health check failed"
    fi
    
    # Test database connection
    if sudo -u "$APP_USER" bash -c "cd '$APP_DIR' && source '$VENV_DIR/bin/activate' && python -c 'from src.database import DatabaseManager; print(DatabaseManager.check_connection())'"; then
        print_success "Database connection test passed"
    else
        print_warning "Database connection test failed"
    fi
    
    # Run application tests
    sudo -u "$APP_USER" bash -c "
        cd '$APP_DIR'
        source '$VENV_DIR/bin/activate'
        python run_tests.py
    " >> "$LOG_FILE" 2>&1 || print_warning "Some application tests failed (check logs)"
}

# Function to display deployment summary
display_summary() {
    local server_ip=$(curl -s http://checkip.amazonaws.com || echo "unknown")
    
    print_success "🎉 Deployment completed successfully!"
    echo ""
    echo "==============================================================================="
    echo "                     TGE MONITOR DEPLOYMENT SUMMARY"
    echo "==============================================================================="
    echo ""
    echo "🌐 ACCESS INFORMATION:"
    echo "   API Documentation: http://$server_ip/docs"
    echo "   Health Check:      http://$server_ip/health"
    echo "   WebSocket:         ws://$server_ip/ws"
    echo ""
    echo "📁 IMPORTANT FILES:"
    echo "   Application Directory: $APP_DIR"
    echo "   Environment Config:    $APP_DIR/.env"
    echo "   Credentials:           $APP_DIR/DEPLOYMENT_CREDENTIALS.txt"
    echo "   Logs Directory:        $APP_DIR/logs/"
    echo ""
    echo "🔧 SERVICES:"
    echo "   API Service:    sudo systemctl status tge-monitor-api"
    echo "   Worker Service: sudo systemctl status tge-monitor-worker"
    echo "   PostgreSQL:     sudo systemctl status postgresql"
    echo "   Redis:          sudo systemctl status redis"
    echo "   Nginx:          sudo systemctl status nginx"
    echo ""
    echo "📊 MONITORING:"
    echo "   Health Check:   $APP_DIR/health_check.sh"
    echo "   View Logs:      tail -f $APP_DIR/logs/*.log"
    echo "   System Status:  sudo systemctl status tge-monitor-*"
    echo ""
    echo "🛠️  NEXT STEPS:"
    echo "   1. Configure email settings in $APP_DIR/.env"
    echo "   2. Add Twitter API credentials (optional)"
    echo "   3. Setup SSL certificate with Let's Encrypt"
    echo "   4. Review and update firewall rules"
    echo "   5. Setup monitoring alerts"
    echo ""
    echo "⚠️  SECURITY REMINDERS:"
    echo "   1. Change default passwords in $APP_DIR/DEPLOYMENT_CREDENTIALS.txt"
    echo "   2. Configure email SMTP settings"
    echo "   3. Review log files for any errors"
    echo "   4. Setup regular backups offsite"
    echo ""
    echo "==============================================================================="
    
    if [ -f "$APP_DIR/DEPLOYMENT_CREDENTIALS.txt" ]; then
        echo ""
        echo "🔑 GENERATED CREDENTIALS:"
        cat "$APP_DIR/DEPLOYMENT_CREDENTIALS.txt"
        echo ""
        echo "⚠️  IMPORTANT: Save these credentials securely and delete the file!"
    fi
}

# Main deployment function
main() {
    echo "==============================================================================="
    echo "          Enhanced TGE Monitor System - Automated EC2 Deployment"
    echo "==============================================================================="
    echo ""
    echo "This script will automatically deploy the Enhanced TGE Monitor System"
    echo "on this EC2 instance. The process includes:"
    echo ""
    echo "  • System updates and dependency installation"
    echo "  • PostgreSQL and Redis setup"
    echo "  • Python environment configuration"
    echo "  • Application deployment"
    echo "  • Service configuration"
    echo "  • Security hardening"
    echo "  • Monitoring setup"
    echo ""
    
    if ! confirm "Do you want to proceed with the automated deployment?"; then
        echo "Deployment cancelled."
        exit 0
    fi
    
    echo ""
    print_status "Starting automated deployment..."
    echo "Deployment log: $LOG_FILE"
    echo ""
    
    # Check if running as root (should not be)
    if [ "$EUID" -eq 0 ]; then
        print_error "This script should not be run as root"
        print_error "Please run as a regular user with sudo privileges"
        exit 1
    fi
    
    # Check if sudo is available
    if ! sudo -v; then
        print_error "This script requires sudo privileges"
        exit 1
    fi
    
    # Start deployment steps
    install_system_dependencies
    install_python
    install_postgresql
    install_redis
    install_nginx
    setup_application_user
    clone_repository
    
    # Setup environment and get database password
    db_password=$(setup_environment)
    setup_postgresql "$db_password"
    
    setup_python_environment
    initialize_database
    setup_services
    setup_monitoring
    configure_firewall
    start_services
    
    # Run tests
    print_status "Running final system tests..."
    run_tests
    
    # Display summary
    display_summary
    
    print_success "🚀 Deployment completed! Check the summary above for next steps."
}

# Error handling
trap 'print_error "Deployment failed at line $LINENO. Check $LOG_FILE for details."' ERR

# Run main function
main "$@"