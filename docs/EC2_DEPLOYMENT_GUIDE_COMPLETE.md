# 🚀 Complete EC2 Deployment Guide for Enhanced TGE Monitor System

This guide provides detailed step-by-step instructions for deploying the Enhanced TGE Monitor System on a brand new Amazon EC2 instance.

## 📋 Table of Contents
1. [Prerequisites](#prerequisites)
2. [EC2 Instance Setup](#ec2-instance-setup)
3. [Initial Server Configuration](#initial-server-configuration)
4. [Install Required Software](#install-required-software)
5. [Clone and Configure Application](#clone-and-configure-application)
6. [Database Setup](#database-setup)
7. [Environment Configuration](#environment-configuration)
8. [Install Python Dependencies](#install-python-dependencies)
9. [System Testing](#system-testing)
10. [Production Deployment](#production-deployment)
11. [Monitoring and Maintenance](#monitoring-and-maintenance)

---

## 1. Prerequisites

Before starting, ensure you have:
- AWS account with EC2 access
- SSH key pair for EC2 access
- Domain name (optional, for SSL)
- Email SMTP credentials (for alerts)
- Twitter API credentials (optional)

## 2. EC2 Instance Setup

### Step 1: Launch EC2 Instance

1. **Log into AWS Console** → EC2 → Launch Instance

2. **Choose AMI**: Ubuntu Server 22.04 LTS (64-bit x86)

3. **Instance Type**: 
   - Minimum: t3.medium (2 vCPU, 4 GB RAM)
   - Recommended: t3.large (2 vCPU, 8 GB RAM)

4. **Configure Instance**:
   ```
   - Number of instances: 1
   - Network: Default VPC
   - Auto-assign Public IP: Enable
   ```

5. **Add Storage**: 
   - 30 GB General Purpose SSD (gp3)
   - Delete on termination: Yes (or No for data persistence)

6. **Configure Security Group**:
   ```
   Name: tge-monitor-sg
   
   Inbound Rules:
   - SSH (22) - Your IP
   - HTTP (80) - Anywhere (0.0.0.0/0)
   - HTTPS (443) - Anywhere (0.0.0.0/0) 
   - Custom TCP (8000) - Your IP (for API access)
   - Custom TCP (5432) - Security group ID (for PostgreSQL)
   - Custom TCP (6379) - Security group ID (for Redis)
   ```

7. **Review and Launch**
   - Select your SSH key pair
   - Launch instance

### Step 2: Connect to Instance

```bash
# Make your key readable
chmod 400 your-key.pem

# Connect via SSH
ssh -i your-key.pem ubuntu@your-ec2-public-ip
```

## 3. Initial Server Configuration

### Update System
```bash
# Update package lists
sudo apt update

# Upgrade packages
sudo apt upgrade -y

# Install essential tools
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
    lsb-release
```

### Configure Timezone
```bash
# Set timezone to PST (or your preferred timezone)
sudo timedatectl set-timezone America/Los_Angeles

# Verify
timedatectl
```

### Create Application User
```bash
# Create dedicated user for the application
sudo useradd -m -s /bin/bash tgemonitor

# Add to sudo group (optional)
sudo usermod -aG sudo tgemonitor

# Create application directories
sudo mkdir -p /opt/tge-monitor
sudo chown tgemonitor:tgemonitor /opt/tge-monitor
```

## 4. Install Required Software

### Install Python 3.11
```bash
# Add Python PPA
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Verify installation
python3.11 --version
```

### Install PostgreSQL 15
```bash
# Add PostgreSQL official APT repository
sudo sh -c 'echo "deb https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update

# Install PostgreSQL 15
sudo apt install -y postgresql-15 postgresql-client-15 postgresql-contrib-15

# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verify
sudo systemctl status postgresql
```

### Install Redis
```bash
# Install Redis
sudo apt install -y redis-server

# Configure Redis for production
sudo sed -i 's/supervised no/supervised systemd/g' /etc/redis/redis.conf
sudo sed -i 's/# maxmemory <bytes>/maxmemory 256mb/g' /etc/redis/redis.conf
sudo sed -i 's/# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/g' /etc/redis/redis.conf

# Restart and enable Redis
sudo systemctl restart redis-server
sudo systemctl enable redis-server

# Verify
redis-cli ping
# Should return: PONG
```

### Install Nginx
```bash
# Install Nginx
sudo apt install -y nginx

# Start and enable
sudo systemctl start nginx
sudo systemctl enable nginx
```

### Install Node.js (for additional tools)
```bash
# Install Node.js 18.x
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install PM2 for process management
sudo npm install -g pm2
```

## 5. Clone and Configure Application

### Switch to Application User
```bash
sudo su - tgemonitor
cd /opt/tge-monitor
```

### Clone Repository
```bash
# Clone the repository
git clone https://github.com/yourusername/OCL_Twitter_Scraper.git .

# Or if using SSH
git clone git@github.com:yourusername/OCL_Twitter_Scraper.git .
```

### Create Virtual Environment
```bash
# Create Python virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

## 6. Database Setup

### Configure PostgreSQL
```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL prompt:
-- Create database user
CREATE USER tgemonitor WITH PASSWORD 'your_secure_password';

-- Create database
CREATE DATABASE tge_monitor OWNER tgemonitor;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE tge_monitor TO tgemonitor;

-- Exit
\q
```

### Configure PostgreSQL for Remote Access (if needed)
```bash
# Edit postgresql.conf
sudo vim /etc/postgresql/15/main/postgresql.conf

# Add/modify:
listen_addresses = 'localhost'  # or '*' for all interfaces

# Edit pg_hba.conf
sudo vim /etc/postgresql/15/main/pg_hba.conf

# Add line for local connections:
local   all             tgemonitor                              md5
host    all             tgemonitor      127.0.0.1/32            md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

## 7. Environment Configuration

### Create Environment File
```bash
cd /opt/tge-monitor
cp .env.example .env
vim .env
```

### Configure Environment Variables
```bash
# Database Configuration
DATABASE_URL=postgresql://tgemonitor:your_secure_password@localhost:5432/tge_monitor
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-very-long-random-secret-key-change-this
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=secure_admin_password

# API Configuration
API_PORT=8000
LOG_LEVEL=INFO

# Email Configuration (use your SMTP settings)
SMTP_SERVER=smtp.maileroo.com
SMTP_PORT=587
EMAIL_USER=your_email@domain.com
EMAIL_PASSWORD=your_email_password
RECIPIENT_EMAIL=alerts@yourdomain.com

# Twitter API (if available)
TWITTER_BEARER_TOKEN=your_twitter_bearer_token

# Application Settings
ENVIRONMENT=production
WORKERS=4
```

### Create Required Directories
```bash
mkdir -p logs state reports
chmod 755 logs state reports
```

## 8. Install Python Dependencies

### Install System Dependencies
```bash
# Install required system packages
sudo apt install -y \
    libpq-dev \
    python3.11-dev \
    gcc \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev
```

### Install Python Packages
```bash
# Ensure virtual environment is activated
source /opt/tge-monitor/venv/bin/activate

# Install all dependencies
pip install -r requirements.txt

# Install additional production dependencies
pip install gunicorn supervisor
```

### Fix NLTK SSL Issue
```bash
# Install certificates
pip install certifi

# Download NLTK data
python3 -c "
import nltk
import ssl
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context
nltk.download('punkt')
"
```

## 9. System Testing

### Test Database Connection
```bash
python3 -c "
from src.database import DatabaseManager
print('Testing database connection...')
if DatabaseManager.check_connection():
    print('✅ Database connection successful!')
else:
    print('❌ Database connection failed!')
"
```

### Initialize Database
```bash
# Run database initialization
python3 -c "
from src.database import init_db
from src.auth import create_admin_user_if_not_exists
from src.database import DatabaseManager

init_db()
print('✅ Database tables created')

with DatabaseManager.get_session() as db:
    create_admin_user_if_not_exists(db)
print('✅ Admin user created')
"
```

### Run System Tests
```bash
# Test all components
python3 run_tests.py

# Run enhanced system demo
python3 demo_enhanced_system.py
```

## 10. Production Deployment

### Create Systemd Service for API
```bash
# Create service file
sudo vim /etc/systemd/system/tge-monitor-api.service
```

Add the following content:
```ini
[Unit]
Description=TGE Monitor API Server
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=exec
User=tgemonitor
Group=tgemonitor
WorkingDirectory=/opt/tge-monitor
Environment="PATH=/opt/tge-monitor/venv/bin"
ExecStart=/opt/tge-monitor/venv/bin/python run_enhanced_system.py --mode server
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Create Systemd Service for Monitor
```bash
# Create monitor service
sudo vim /etc/systemd/system/tge-monitor-worker.service
```

Add the following content:
```ini
[Unit]
Description=TGE Monitor Worker
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=simple
User=tgemonitor
Group=tgemonitor
WorkingDirectory=/opt/tge-monitor
Environment="PATH=/opt/tge-monitor/venv/bin"
ExecStart=/opt/tge-monitor/venv/bin/python -m src.main --mode continuous
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable and Start Services
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable tge-monitor-api
sudo systemctl enable tge-monitor-worker

# Start services
sudo systemctl start tge-monitor-api
sudo systemctl start tge-monitor-worker

# Check status
sudo systemctl status tge-monitor-api
sudo systemctl status tge-monitor-worker
```

### Configure Nginx Reverse Proxy
```bash
# Create Nginx configuration
sudo vim /etc/nginx/sites-available/tge-monitor
```

Add the following content:
```nginx
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain or IP

    # Redirect HTTP to HTTPS (if using SSL)
    # return 301 https://$server_name$request_uri;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
```

Enable the site:
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/tge-monitor /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### Setup SSL with Let's Encrypt (Optional)
```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is automatically configured
```

### Configure Firewall
```bash
# Install UFW if not already installed
sudo apt install -y ufw

# Configure firewall rules
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw --force enable

# Check status
sudo ufw status
```

## 11. Monitoring and Maintenance

### Setup Log Rotation
```bash
# Create logrotate configuration
sudo vim /etc/logrotate.d/tge-monitor
```

Add:
```
/opt/tge-monitor/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 tgemonitor tgemonitor
    sharedscripts
    postrotate
        systemctl reload tge-monitor-api > /dev/null 2>&1 || true
        systemctl reload tge-monitor-worker > /dev/null 2>&1 || true
    endscript
}
```

### Setup Monitoring with PM2 (Alternative)
```bash
# Create PM2 ecosystem file
vim /opt/tge-monitor/ecosystem.config.js
```

Add:
```javascript
module.exports = {
  apps: [
    {
      name: 'tge-api',
      script: 'run_enhanced_system.py',
      args: '--mode server',
      interpreter: '/opt/tge-monitor/venv/bin/python',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production'
      }
    },
    {
      name: 'tge-worker',
      script: '-m',
      args: 'src.main --mode continuous',
      interpreter: '/opt/tge-monitor/venv/bin/python',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M'
    }
  ]
};
```

Start with PM2:
```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

### Setup CloudWatch Monitoring (Optional)
```bash
# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i -E ./amazon-cloudwatch-agent.deb

# Configure and start agent
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-config-wizard
```

### Create Health Check Script
```bash
vim /opt/tge-monitor/health_check.sh
```

Add:
```bash
#!/bin/bash
# Health check script

API_HEALTH=$(curl -s http://localhost:8000/health | grep -c "healthy")
WORKER_STATUS=$(systemctl is-active tge-monitor-worker)
DB_CHECK=$(sudo -u postgres psql -t -c "SELECT 1" 2>/dev/null | grep -c "1")
REDIS_CHECK=$(redis-cli ping 2>/dev/null | grep -c "PONG")

if [ "$API_HEALTH" -eq 1 ] && [ "$WORKER_STATUS" = "active" ] && [ "$DB_CHECK" -eq 1 ] && [ "$REDIS_CHECK" -eq 1 ]; then
    echo "✅ All systems operational"
    exit 0
else
    echo "❌ System health check failed"
    echo "API: $API_HEALTH, Worker: $WORKER_STATUS, DB: $DB_CHECK, Redis: $REDIS_CHECK"
    exit 1
fi
```

Make executable:
```bash
chmod +x /opt/tge-monitor/health_check.sh

# Add to crontab for regular checks
crontab -e
# Add: */5 * * * * /opt/tge-monitor/health_check.sh || systemctl restart tge-monitor-api tge-monitor-worker
```

### Backup Strategy
```bash
# Create backup script
vim /opt/tge-monitor/backup.sh
```

Add:
```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/tge-monitor"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
sudo -u postgres pg_dump tge_monitor | gzip > "$BACKUP_DIR/db_backup_$DATE.sql.gz"

# Backup application state
tar -czf "$BACKUP_DIR/state_backup_$DATE.tar.gz" /opt/tge-monitor/state/

# Keep only last 7 days of backups
find $BACKUP_DIR -type f -mtime +7 -delete
```

Make executable and schedule:
```bash
chmod +x /opt/tge-monitor/backup.sh

# Add to crontab
crontab -e
# Add: 0 2 * * * /opt/tge-monitor/backup.sh
```

## 🎯 Verification Steps

After deployment, verify everything is working:

1. **Check Service Status**:
   ```bash
   sudo systemctl status tge-monitor-api
   sudo systemctl status tge-monitor-worker
   sudo systemctl status postgresql
   sudo systemctl status redis
   sudo systemctl status nginx
   ```

2. **Test API Endpoints**:
   ```bash
   # Health check
   curl http://localhost:8000/health
   
   # API docs
   curl http://your-domain.com/docs
   ```

3. **Check Logs**:
   ```bash
   # API logs
   sudo journalctl -u tge-monitor-api -f
   
   # Worker logs
   sudo journalctl -u tge-monitor-worker -f
   
   # Application logs
   tail -f /opt/tge-monitor/logs/*.log
   ```

4. **Test Monitoring**:
   ```bash
   # Run test mode
   cd /opt/tge-monitor
   source venv/bin/activate
   python -m src.main --mode test
   ```

## 🔒 Security Hardening

1. **Disable Root SSH**:
   ```bash
   sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/g' /etc/ssh/sshd_config
   sudo systemctl restart sshd
   ```

2. **Setup Fail2ban**:
   ```bash
   sudo apt install -y fail2ban
   sudo systemctl enable fail2ban
   sudo systemctl start fail2ban
   ```

3. **Regular Updates**:
   ```bash
   # Create update script
   sudo vim /etc/cron.weekly/security-updates
   ```
   
   Add:
   ```bash
   #!/bin/bash
   apt update
   apt upgrade -y
   ```

4. **Monitor Security Logs**:
   ```bash
   # Check authentication logs
   sudo tail -f /var/log/auth.log
   
   # Check application security
   grep -i "error\|warning\|critical" /opt/tge-monitor/logs/*.log
   ```

## 📊 Performance Tuning

1. **PostgreSQL Tuning**:
   ```bash
   # Edit PostgreSQL config
   sudo vim /etc/postgresql/15/main/postgresql.conf
   
   # Add optimizations:
   shared_buffers = 256MB
   effective_cache_size = 1GB
   work_mem = 4MB
   maintenance_work_mem = 64MB
   ```

2. **Redis Tuning**:
   ```bash
   # Already configured in installation step
   # Additional tuning in /etc/redis/redis.conf if needed
   ```

3. **Python Application**:
   ```bash
   # Use production WSGI server
   # Already configured with gunicorn
   ```

## 🚨 Troubleshooting

### Common Issues:

1. **Database Connection Failed**:
   ```bash
   # Check PostgreSQL status
   sudo systemctl status postgresql
   
   # Check connection
   sudo -u postgres psql -c "SELECT 1"
   
   # Check logs
   sudo tail -f /var/log/postgresql/*.log
   ```

2. **API Not Responding**:
   ```bash
   # Check service
   sudo systemctl status tge-monitor-api
   
   # Check port
   sudo netstat -tlnp | grep 8000
   
   # Restart service
   sudo systemctl restart tge-monitor-api
   ```

3. **High Memory Usage**:
   ```bash
   # Check memory
   free -h
   
   # Find memory-hungry processes
   ps aux --sort=-%mem | head
   
   # Restart services
   sudo systemctl restart tge-monitor-api tge-monitor-worker
   ```

## 🎉 Deployment Complete!

Your Enhanced TGE Monitor System is now fully deployed and operational. 

Access points:
- **API Documentation**: http://your-domain.com/docs
- **Health Check**: http://your-domain.com/health
- **WebSocket**: ws://your-domain.com/ws

Monitor the logs and health checks regularly to ensure smooth operation.

---

For support or issues, refer to the project documentation or create an issue in the GitHub repository.