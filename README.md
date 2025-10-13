# 🚀 Enhanced TGE Monitor System

A production-grade Token Generation Event (TGE) monitoring system with real-time alerts, machine learning-based content analysis, RESTful API, WebSocket support, and comprehensive monitoring infrastructure.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7+-red.svg)](https://redis.io/)
[![Tests](https://img.shields.io/badge/tests-599%20passing-brightgreen.svg)](tests/)

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Prerequisites](#-prerequisites)
- [Quick Start](#-quick-start)
- [Complete Setup Guide](#-complete-setup-guide)
- [AWS EC2 Deployment](#-aws-ec2-deployment-guide)
- [Production Configuration](#-production-configuration)
- [API Reference](#-api-reference)
- [Monitoring & Logging](#-monitoring--logging)
- [Security](#-security)
- [Performance Optimization](#-performance-optimization)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

## ✨ Features

### Core Capabilities
- **Real-Time Monitoring** - Twitter and news feed monitoring with multi-source aggregation
- **RESTful API** - FastAPI with automatic OpenAPI documentation
- **WebSocket Alerts** - Real-time push notifications with subscription management
- **Machine Learning** - Advanced content analysis with confidence scoring
- **Multi-User Support** - JWT authentication with role-based access control
- **Rate Limiting** - Distributed rate limiting with Redis (fixed window, sliding window, token bucket)
- **Caching Layer** - Redis-based caching for high-performance data access
- **Database ORM** - SQLAlchemy with PostgreSQL for ACID compliance
- **Test Coverage** - 599 passing unit tests with 97% pass rate

### Advanced Features
- **Production Monitoring** - Prometheus metrics, Grafana dashboards, health checks
- **Horizontal Scaling** - Load-balanced API servers and worker processes
- **Container Support** - Docker and Docker Compose with multi-stage builds
- **CI/CD Ready** - GitHub Actions, automated testing, deployment pipelines
- **Backup & Recovery** - Automated database backups with point-in-time recovery
- **Security Hardening** - HTTPS/TLS, rate limiting, input validation, SQL injection prevention
- **Email Notifications** - Configurable email alerts for high-confidence TGE events
- **API Key Management** - Granular API keys with usage tracking and expiration

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Load Balancer (nginx)                      │
│                     SSL/TLS Termination                           │
└───────────────────────────┬──────────────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            │                               │
┌───────────▼─────────┐       ┌─────────────▼──────────┐
│   API Server 1      │       │   API Server 2         │
│   FastAPI + Uvicorn │       │   FastAPI + Uvicorn    │
│   WebSocket Handler │       │   WebSocket Handler    │
└───────────┬─────────┘       └─────────────┬──────────┘
            │                               │
            └───────────────┬───────────────┘
                            │
        ┌───────────────────┴───────────────────────┐
        │                                           │
┌───────▼────────────┐                 ┌───────────▼──────────┐
│  Worker Process 1   │                │  Worker Process 2     │
│  Twitter Monitor    │                │  News Scraper         │
│  Alert Processing   │                │  Data Quality Agent   │
└───────┬────────────┘                 └───────────┬──────────┘
        │                                           │
        └───────────────────┬───────────────────────┘
                            │
        ┌───────────────────┴───────────────────────┐
        │                                           │
┌───────▼────────────┐                 ┌───────────▼──────────┐
│   PostgreSQL 15    │                 │      Redis 7         │
│   Primary Database │                 │   Cache + Sessions   │
│   ACID Compliance  │                 │   Rate Limiting      │
└────────────────────┘                 └──────────────────────┘
        │                                           │
┌───────▼────────────┐                 ┌───────────▼──────────┐
│  Prometheus        │                 │     Grafana          │
│  Metrics Storage   │                 │   Dashboards         │
└────────────────────┘                 └──────────────────────┘
```

## 📊 Database Schema

```sql
-- Core Tables
User (id, username, email, hashed_password, is_admin, created_at)
APIKey (id, user_id, key_hash, name, expires_at, usage_count)
Company (id, name, aliases[], tokens[], priority, status)
Alert (id, company_id, user_id, title, content, source, confidence, urgency_level)
Feed (id, name, url, type, priority, success_count, failure_count)
MonitoringSession (id, session_id, status, feeds_processed, alerts_generated)
SystemMetrics (id, timestamp, metric_type, metric_name, value, tags{})
```

## 🔧 Prerequisites

### Required Software
- **Python** 3.11 or higher
- **PostgreSQL** 15 or higher
- **Redis** 7 or higher
- **Node.js** 18+ (for web dashboard - optional)
- **Docker** 20.10+ and Docker Compose 2.0+ (for containerized deployment)

### System Requirements
- **Minimum**: 2 CPU cores, 4GB RAM, 20GB disk
- **Recommended**: 4 CPU cores, 8GB RAM, 50GB disk
- **Production**: 8+ CPU cores, 16GB+ RAM, 100GB+ SSD

### API Keys & Services
- **Twitter API** - Bearer token with elevated access
- **Email Service** - SMTP credentials for notifications (Gmail, SendGrid, etc.)
- **News Feeds** - RSS feed URLs (provided in config)

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/OCL_Twitter_Scraper.git
cd OCL_Twitter_Scraper
```

### 2. Create Virtual Environment
```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
nano .env  # Edit with your configuration
```

**Minimum Required Configuration:**
```bash
# Database
DATABASE_URL=postgresql://tge_user:secure_password@localhost:5432/tge_monitor

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=$(openssl rand -hex 32)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_admin_password

# Twitter API
TWITTER_BEARER_TOKEN=your_twitter_bearer_token

# Email Notifications
EMAIL_USER=alerts@yourdomain.com
EMAIL_PASSWORD=your_app_password
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
```

### 5. Initialize Database
```bash
# Start PostgreSQL and Redis (if not running)
sudo systemctl start postgresql redis

# Create database
sudo -u postgres psql -c "CREATE DATABASE tge_monitor;"
sudo -u postgres psql -c "CREATE USER tge_user WITH PASSWORD 'secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE tge_monitor TO tge_user;"

# Run database initialization
python -c "
from src.database import DatabaseManager
from src.models import Base
DatabaseManager.create_tables()
print('Database initialized successfully!')
"
```

### 6. Create Admin User
```bash
python -c "
import asyncio
from src.auth import create_admin_user_if_not_exists
from src.database import DatabaseManager

async def init_admin():
    async for db in DatabaseManager.get_db():
        await create_admin_user_if_not_exists(db)
        print('Admin user created!')
        break

asyncio.run(init_admin())
"
```

### 7. Start the System
```bash
# Option A: Development mode
python -m uvicorn src.api:app --reload --host 0.0.0.0 --port 8000

# Option B: Production mode
gunicorn src.api:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000

# Option C: With monitoring worker
python src/main_optimized_db.py --mode production &
python -m uvicorn src.api:app --host 0.0.0.0 --port 8000
```

### 8. Verify Installation
```bash
# Check API health
curl http://localhost:8000/health

# Access API documentation
open http://localhost:8000/docs

# Test authentication
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_secure_admin_password"}'
```

## 📚 Complete Setup Guide

### Step 1: System Preparation

#### Update System Packages
```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential python3.11 python3.11-venv python3-pip \
    postgresql-15 postgresql-contrib redis-server nginx certbot \
    git curl wget vim htop

# CentOS/RHEL
sudo yum update -y
sudo yum install -y python311 python3-pip postgresql15-server redis nginx git
```

#### Configure PostgreSQL
```bash
# Initialize PostgreSQL
sudo postgresql-setup --initdb

# Start and enable service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Configure authentication (edit /var/lib/pgsql/data/pg_hba.conf)
sudo sed -i 's/peer/md5/g' /var/lib/pgsql/data/pg_hba.conf
sudo sed -i 's/ident/md5/g' /var/lib/pgsql/data/pg_hba.conf

# Restart PostgreSQL
sudo systemctl restart postgresql

# Create database and user
sudo -u postgres psql <<EOF
CREATE DATABASE tge_monitor;
CREATE USER tge_user WITH ENCRYPTED PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE tge_monitor TO tge_user;
ALTER USER tge_user WITH SUPERUSER;
\q
EOF
```

#### Configure Redis
```bash
# Edit Redis configuration
sudo nano /etc/redis/redis.conf

# Recommended settings for production:
# bind 127.0.0.1
# protected-mode yes
# requirepass your_redis_password
# maxmemory 2gb
# maxmemory-policy allkeys-lru

# Start and enable Redis
sudo systemctl start redis
sudo systemctl enable redis
```

### Step 2: Application Setup

#### Install Application
```bash
# Create application directory
sudo mkdir -p /opt/tge-monitor
sudo chown $USER:$USER /opt/tge-monitor
cd /opt/tge-monitor

# Clone repository
git clone https://github.com/yourusername/OCL_Twitter_Scraper.git .

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip wheel setuptools
pip install -r requirements.txt

# Install production server
pip install gunicorn uvicorn[standard]
```

#### Configure Application
```bash
# Create environment file
cat > /opt/tge-monitor/.env <<EOF
# Database Configuration
DATABASE_URL=postgresql://tge_user:your_secure_password@localhost:5432/tge_monitor
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis Configuration
REDIS_URL=redis://:your_redis_password@localhost:6379/0
REDIS_MAX_CONNECTIONS=50

# Security
SECRET_KEY=$(openssl rand -hex 32)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=$(openssl rand -base64 32)
JWT_EXPIRATION_HOURS=24
API_KEY_EXPIRATION_DAYS=90

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
LOG_LEVEL=INFO
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Twitter API
TWITTER_BEARER_TOKEN=your_twitter_bearer_token
TWITTER_RATE_LIMIT=300
TWITTER_RATE_WINDOW=900

# Email Notifications
EMAIL_ENABLED=true
EMAIL_USER=alerts@yourdomain.com
EMAIL_PASSWORD=your_app_password
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_FROM=TGE Monitor <alerts@yourdomain.com>
EMAIL_RECIPIENTS=admin@yourdomain.com,team@yourdomain.com

# Monitoring Configuration
MONITORING_ENABLED=true
MONITORING_INTERVAL=300
METRICS_RETENTION_DAYS=30

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_STRATEGY=sliding_window
RATE_LIMIT_API_GENERAL=1000:3600
RATE_LIMIT_API_ALERTS=100:3600
RATE_LIMIT_WEBSOCKET=10:60

# News Feed Sources
NEWS_FEEDS=https://theblock.co/rss.xml,https://decrypt.co/feed,https://cointelegraph.com/rss

# Performance
WORKER_PROCESSES=2
MAX_CONCURRENT_REQUESTS=100
REQUEST_TIMEOUT=30
EOF

# Secure environment file
chmod 600 /opt/tge-monitor/.env
```

#### Initialize Database Schema
```bash
cd /opt/tge-monitor
source venv/bin/activate

# Run migrations
python -c "
from src.database import DatabaseManager
from src.models import Base
from sqlalchemy import create_engine
import os

engine = create_engine(os.getenv('DATABASE_URL'))
Base.metadata.create_all(engine)
print('✓ Database tables created')
"

# Create admin user
python -c "
import asyncio
import os
from src.auth import create_admin_user_if_not_exists
from src.database import DatabaseManager

async def setup():
    async for db in DatabaseManager.get_db():
        await create_admin_user_if_not_exists(db)
        print('✓ Admin user created')
        print(f'Username: {os.getenv(\"ADMIN_USERNAME\")}')
        print(f'Password: {os.getenv(\"ADMIN_PASSWORD\")}')
        break

asyncio.run(setup())
"

# Load sample companies
python demo_enhanced_system.py
```

### Step 3: Systemd Service Configuration

#### Create API Service
```bash
sudo tee /etc/systemd/system/tge-api.service <<EOF
[Unit]
Description=TGE Monitor API Server
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=notify
User=$USER
Group=$USER
WorkingDirectory=/opt/tge-monitor
Environment="PATH=/opt/tge-monitor/venv/bin"
EnvironmentFile=/opt/tge-monitor/.env
ExecStart=/opt/tge-monitor/venv/bin/gunicorn src.api:app \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    -b 0.0.0.0:8000 \
    --access-logfile /var/log/tge-monitor/api-access.log \
    --error-logfile /var/log/tge-monitor/api-error.log \
    --log-level info
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

#### Create Worker Service
```bash
sudo tee /etc/systemd/system/tge-worker.service <<EOF
[Unit]
Description=TGE Monitor Background Worker
After=network.target postgresql.service redis.service tge-api.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=/opt/tge-monitor
Environment="PATH=/opt/tge-monitor/venv/bin"
EnvironmentFile=/opt/tge-monitor/.env
ExecStart=/opt/tge-monitor/venv/bin/python src/main_optimized_db.py --mode production
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

#### Enable and Start Services
```bash
# Create log directory
sudo mkdir -p /var/log/tge-monitor
sudo chown $USER:$USER /var/log/tge-monitor

# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable tge-api tge-worker

# Start services
sudo systemctl start tge-api tge-worker

# Check status
sudo systemctl status tge-api tge-worker

# View logs
sudo journalctl -u tge-api -f
sudo journalctl -u tge-worker -f
```

### Step 4: Nginx Reverse Proxy Setup

```bash
# Create Nginx configuration
sudo tee /etc/nginx/sites-available/tge-monitor <<'EOF'
# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;
limit_req_zone $binary_remote_addr zone=ws_limit:10m rate=10r/s;

# Upstream API servers (for load balancing)
upstream tge_api {
    least_conn;
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    # Add more servers for horizontal scaling:
    # server 127.0.0.1:8001 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

# HTTP -> HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com www.yourdomain.com;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Logging
    access_log /var/log/nginx/tge-monitor-access.log;
    error_log /var/log/nginx/tge-monitor-error.log;

    # API endpoints
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;

        proxy_pass http://tge_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket endpoint
    location /ws {
        limit_req zone=ws_limit burst=5 nodelay;

        proxy_pass http://tge_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket timeouts
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }

    # Health check (allow without rate limiting)
    location /health {
        proxy_pass http://tge_api;
        access_log off;
    }

    # Static files (if you add a web dashboard)
    location /static/ {
        alias /opt/tge-monitor/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/tge-monitor /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Obtain SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Reload Nginx
sudo systemctl reload nginx
```

## 🌩️ AWS EC2 Deployment Guide

### Step 1: Launch EC2 Instance

#### 1.1 Create EC2 Instance
```bash
# Using AWS CLI
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.large \
  --key-name your-key-pair \
  --security-group-ids sg-xxxxxxxxx \
  --subnet-id subnet-xxxxxxxxx \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":50,"VolumeType":"gp3","Iops":3000,"Throughput":125}}]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=TGE-Monitor-Production}]' \
  --user-data file://user-data.sh
```

**Recommended Instance Types:**
- **Development**: `t3.medium` (2 vCPU, 4GB RAM) - $30/month
- **Production**: `t3.large` (2 vCPU, 8GB RAM) - $60/month
- **High Traffic**: `t3.xlarge` (4 vCPU, 16GB RAM) - $120/month
- **Enterprise**: `c5.2xlarge` (8 vCPU, 16GB RAM) - $250/month

#### 1.2 Configure Security Group

Create security group with the following rules:

**Inbound Rules:**
```bash
# SSH (restrict to your IP)
Port 22, Protocol TCP, Source: YOUR_IP/32

# HTTP (for Let's Encrypt)
Port 80, Protocol TCP, Source: 0.0.0.0/0

# HTTPS (API access)
Port 443, Protocol TCP, Source: 0.0.0.0/0

# PostgreSQL (only from application security group)
Port 5432, Protocol TCP, Source: sg-app-xxxxxxxxx

# Redis (only from application security group)
Port 6379, Protocol TCP, Source: sg-app-xxxxxxxxx

# Monitoring (Prometheus - optional, restrict to monitoring subnet)
Port 9090, Protocol TCP, Source: 10.0.2.0/24

# Grafana (optional, restrict to VPN)
Port 3000, Protocol TCP, Source: VPN_IP/32
```

**Outbound Rules:**
```bash
# Allow all outbound traffic
All traffic, All protocols, Destination: 0.0.0.0/0
```

#### 1.3 Create user-data.sh
```bash
#!/bin/bash
set -e

# Update system
apt-get update
apt-get upgrade -y

# Install required packages
apt-get install -y \
    python3.11 python3.11-venv python3-pip \
    postgresql-15 postgresql-contrib \
    redis-server \
    nginx \
    certbot python3-certbot-nginx \
    git curl wget vim htop \
    awscli \
    build-essential

# Configure CloudWatch agent (optional)
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
dpkg -i -E ./amazon-cloudwatch-agent.deb

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker ubuntu

# Create application user
useradd -m -s /bin/bash tge-monitor
mkdir -p /opt/tge-monitor
chown tge-monitor:tge-monitor /opt/tge-monitor

echo "EC2 instance initialized successfully!"
```

### Step 2: RDS PostgreSQL Setup (Recommended for Production)

#### 2.1 Create RDS Instance
```bash
aws rds create-db-instance \
  --db-instance-identifier tge-monitor-db \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 15.4 \
  --master-username tge_admin \
  --master-user-password 'YourSecurePassword123!' \
  --allocated-storage 100 \
  --storage-type gp3 \
  --storage-encrypted \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "mon:04:00-mon:05:00" \
  --multi-az \
  --vpc-security-group-ids sg-database-xxxxxxxxx \
  --db-subnet-group-name tge-monitor-db-subnet \
  --publicly-accessible false \
  --tags Key=Name,Value=TGE-Monitor-Database
```

#### 2.2 Configure Database
```bash
# Connect to RDS instance
psql -h tge-monitor-db.xxxxxxxxx.us-east-1.rds.amazonaws.com \
     -U tge_admin -d postgres

-- Create application database and user
CREATE DATABASE tge_monitor;
CREATE USER tge_user WITH ENCRYPTED PASSWORD 'SecureAppPassword456!';
GRANT ALL PRIVILEGES ON DATABASE tge_monitor TO tge_user;

-- Connect to application database
\c tge_monitor

-- Grant schema permissions
GRANT ALL ON SCHEMA public TO tge_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO tge_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO tge_user;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

\q
```

### Step 3: ElastiCache Redis Setup (Recommended for Production)

#### 3.1 Create ElastiCache Cluster
```bash
aws elasticache create-replication-group \
  --replication-group-id tge-monitor-redis \
  --replication-group-description "TGE Monitor Redis Cluster" \
  --engine redis \
  --engine-version 7.0 \
  --cache-node-type cache.t3.medium \
  --num-cache-clusters 2 \
  --automatic-failover-enabled \
  --multi-az-enabled \
  --cache-subnet-group-name tge-monitor-cache-subnet \
  --security-group-ids sg-cache-xxxxxxxxx \
  --at-rest-encryption-enabled \
  --transit-encryption-enabled \
  --auth-token "YourRedisAuthToken789!" \
  --snapshot-retention-limit 5 \
  --snapshot-window "03:00-05:00" \
  --tags Key=Name,Value=TGE-Monitor-Redis
```

### Step 4: Application Deployment

#### 4.1 Connect to EC2 Instance
```bash
# SSH into instance
ssh -i ~/.ssh/your-key-pair.pem ubuntu@ec2-xx-xx-xx-xx.compute.amazonaws.com

# Switch to application user
sudo su - tge-monitor
```

#### 4.2 Deploy Application
```bash
cd /opt/tge-monitor

# Clone repository
git clone https://github.com/yourusername/OCL_Twitter_Scraper.git .

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn uvicorn[standard]

# Create .env file with AWS resources
cat > .env <<EOF
# Database (RDS)
DATABASE_URL=postgresql://tge_user:SecureAppPassword456!@tge-monitor-db.xxxxxxxxx.us-east-1.rds.amazonaws.com:5432/tge_monitor

# Redis (ElastiCache)
REDIS_URL=redis://:YourRedisAuthToken789!@tge-monitor-redis.xxxxxx.cache.amazonaws.com:6379/0

# Security
SECRET_KEY=$(openssl rand -hex 32)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=$(openssl rand -base64 32)

# AWS Configuration
AWS_REGION=us-east-1
AWS_S3_BUCKET=tge-monitor-backups
AWS_CLOUDWATCH_ENABLED=true

# Twitter API
TWITTER_BEARER_TOKEN=your_twitter_bearer_token

# Email (using SES)
EMAIL_ENABLED=true
EMAIL_BACKEND=ses
EMAIL_FROM=alerts@yourdomain.com
EMAIL_RECIPIENTS=admin@yourdomain.com

# Application
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
LOG_LEVEL=INFO

# Production settings
ENV=production
DEBUG=false
CORS_ORIGINS=https://yourdomain.com
EOF

chmod 600 .env

# Initialize database
python -c "
from src.database import DatabaseManager
from src.models import Base
DatabaseManager.create_tables()
"

# Create admin user
python -c "
import asyncio
from src.auth import create_admin_user_if_not_exists
from src.database import DatabaseManager

async def setup():
    async for db in DatabaseManager.get_db():
        await create_admin_user_if_not_exists(db)
        break

asyncio.run(setup())
"
```

#### 4.3 Configure Systemd Services
```bash
# Exit to ubuntu user
exit

# Create systemd service files (as root)
sudo tee /etc/systemd/system/tge-api.service <<EOF
[Unit]
Description=TGE Monitor API Server
After=network.target

[Service]
Type=notify
User=tge-monitor
Group=tge-monitor
WorkingDirectory=/opt/tge-monitor
Environment="PATH=/opt/tge-monitor/venv/bin"
EnvironmentFile=/opt/tge-monitor/.env
ExecStart=/opt/tge-monitor/venv/bin/gunicorn src.api:app \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    -b 0.0.0.0:8000 \
    --access-logfile /var/log/tge-monitor/api-access.log \
    --error-logfile /var/log/tge-monitor/api-error.log
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/tge-worker.service <<EOF
[Unit]
Description=TGE Monitor Worker
After=network.target tge-api.service

[Service]
Type=simple
User=tge-monitor
Group=tge-monitor
WorkingDirectory=/opt/tge-monitor
Environment="PATH=/opt/tge-monitor/venv/bin"
EnvironmentFile=/opt/tge-monitor/.env
ExecStart=/opt/tge-monitor/venv/bin/python src/main_optimized_db.py --mode production
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create log directory
sudo mkdir -p /var/log/tge-monitor
sudo chown tge-monitor:tge-monitor /var/log/tge-monitor

# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable tge-api tge-worker
sudo systemctl start tge-api tge-worker
sudo systemctl status tge-api tge-worker
```

#### 4.4 Configure Nginx with SSL
```bash
# Configure Nginx (see previous Nginx configuration section)
sudo nano /etc/nginx/sites-available/tge-monitor

# Enable site
sudo ln -s /etc/nginx/sites-available/tge-monitor /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Obtain SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Start Nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

### Step 5: CloudWatch Monitoring Setup

#### 5.1 Configure CloudWatch Agent
```bash
# Create CloudWatch config
sudo tee /opt/aws/amazon-cloudwatch-agent/etc/config.json <<'EOF'
{
  "agent": {
    "metrics_collection_interval": 60,
    "run_as_user": "cwagent"
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/tge-monitor/api-access.log",
            "log_group_name": "/tge-monitor/api/access",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/var/log/tge-monitor/api-error.log",
            "log_group_name": "/tge-monitor/api/error",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/var/log/nginx/tge-monitor-access.log",
            "log_group_name": "/tge-monitor/nginx/access",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  },
  "metrics": {
    "namespace": "TGEMonitor",
    "metrics_collected": {
      "cpu": {
        "measurement": [
          {"name": "cpu_usage_idle", "rename": "CPU_IDLE", "unit": "Percent"},
          {"name": "cpu_usage_iowait", "rename": "CPU_IOWAIT", "unit": "Percent"}
        ],
        "metrics_collection_interval": 60
      },
      "disk": {
        "measurement": [
          {"name": "used_percent", "rename": "DISK_USED", "unit": "Percent"}
        ],
        "metrics_collection_interval": 60,
        "resources": ["*"]
      },
      "mem": {
        "measurement": [
          {"name": "mem_used_percent", "rename": "MEM_USED", "unit": "Percent"}
        ],
        "metrics_collection_interval": 60
      },
      "netstat": {
        "measurement": [
          {"name": "tcp_established", "rename": "TCP_CONNECTIONS", "unit": "Count"}
        ],
        "metrics_collection_interval": 60
      }
    }
  }
}
EOF

# Start CloudWatch agent
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -s \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/config.json
```

#### 5.2 Create CloudWatch Alarms
```bash
# High CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name tge-monitor-high-cpu \
  --alarm-description "Alert when CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:tge-monitor-alerts

# High memory alarm
aws cloudwatch put-metric-alarm \
  --alarm-name tge-monitor-high-memory \
  --alarm-description "Alert when memory exceeds 85%" \
  --metric-name MEM_USED \
  --namespace TGEMonitor \
  --statistic Average \
  --period 300 \
  --threshold 85 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:tge-monitor-alerts

# API error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name tge-monitor-api-errors \
  --alarm-description "Alert on high API error rate" \
  --metric-name 5XXError \
  --namespace AWS/ApiGateway \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:tge-monitor-alerts
```

### Step 6: Backup Configuration

#### 6.1 Database Backup Script
```bash
sudo tee /opt/tge-monitor/backup-database.sh <<'EOF'
#!/bin/bash
set -e

# Configuration
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/tge-monitor"
S3_BUCKET="s3://tge-monitor-backups"
DB_HOST="tge-monitor-db.xxxxxxxxx.us-east-1.rds.amazonaws.com"
DB_NAME="tge_monitor"
DB_USER="tge_user"

# Create backup directory
mkdir -p $BACKUP_DIR

# Perform backup
PGPASSWORD=$DB_PASSWORD pg_dump \
  -h $DB_HOST \
  -U $DB_USER \
  -d $DB_NAME \
  -F c \
  -f $BACKUP_DIR/tge_monitor_$TIMESTAMP.dump

# Compress backup
gzip $BACKUP_DIR/tge_monitor_$TIMESTAMP.dump

# Upload to S3
aws s3 cp $BACKUP_DIR/tge_monitor_$TIMESTAMP.dump.gz \
  $S3_BUCKET/database/tge_monitor_$TIMESTAMP.dump.gz \
  --storage-class STANDARD_IA

# Remove local backups older than 7 days
find $BACKUP_DIR -name "*.dump.gz" -mtime +7 -delete

echo "Backup completed: tge_monitor_$TIMESTAMP.dump.gz"
EOF

chmod +x /opt/tge-monitor/backup-database.sh
```

#### 6.2 Configure Cron Jobs
```bash
# Edit crontab
sudo crontab -e

# Add backup jobs
# Daily database backup at 2 AM
0 2 * * * /opt/tge-monitor/backup-database.sh >> /var/log/tge-monitor/backup.log 2>&1

# Weekly full system backup at 3 AM Sunday
0 3 * * 0 tar -czf /var/backups/tge-monitor/system_$(date +\%Y\%m\%d).tar.gz /opt/tge-monitor --exclude=venv --exclude=.git && aws s3 cp /var/backups/tge-monitor/system_$(date +\%Y\%m\%d).tar.gz s3://tge-monitor-backups/system/

# Clean old logs daily at 1 AM
0 1 * * * find /var/log/tge-monitor -name "*.log" -mtime +30 -delete

# Restart services weekly at 4 AM Monday (optional)
0 4 * * 1 systemctl restart tge-api tge-worker
```

### Step 7: Load Balancer Setup (Optional - for High Availability)

#### 7.1 Create Application Load Balancer
```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name tge-monitor-alb \
  --subnets subnet-xxxxxxxxx subnet-yyyyyyyyy \
  --security-groups sg-alb-xxxxxxxxx \
  --scheme internet-facing \
  --type application \
  --ip-address-type ipv4 \
  --tags Key=Name,Value=TGE-Monitor-ALB

# Create target group
aws elbv2 create-target-group \
  --name tge-monitor-targets \
  --protocol HTTP \
  --port 8000 \
  --vpc-id vpc-xxxxxxxxx \
  --health-check-enabled \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3

# Register targets
aws elbv2 register-targets \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-1:ACCOUNT_ID:targetgroup/tge-monitor-targets/xxxxxxxxx \
  --targets Id=i-xxxxxxxxx Id=i-yyyyyyyyy

# Create HTTPS listener
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:ACCOUNT_ID:loadbalancer/app/tge-monitor-alb/xxxxxxxxx \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:us-east-1:ACCOUNT_ID:certificate/xxxxxxxxx \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-east-1:ACCOUNT_ID:targetgroup/tge-monitor-targets/xxxxxxxxx
```

### Step 8: Auto Scaling Configuration

#### 8.1 Create Launch Template
```bash
aws ec2 create-launch-template \
  --launch-template-name tge-monitor-template \
  --version-description "TGE Monitor v1.0" \
  --launch-template-data '{
    "ImageId": "ami-0c55b159cbfafe1f0",
    "InstanceType": "t3.large",
    "KeyName": "your-key-pair",
    "SecurityGroupIds": ["sg-xxxxxxxxx"],
    "IamInstanceProfile": {"Arn": "arn:aws:iam::ACCOUNT_ID:instance-profile/TGEMonitorEC2Role"},
    "UserData": "'$(base64 -w 0 user-data.sh)'"
  }'
```

#### 8.2 Create Auto Scaling Group
```bash
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name tge-monitor-asg \
  --launch-template LaunchTemplateName=tge-monitor-template,Version='$Latest' \
  --min-size 2 \
  --max-size 10 \
  --desired-capacity 2 \
  --default-cooldown 300 \
  --health-check-type ELB \
  --health-check-grace-period 300 \
  --vpc-zone-identifier "subnet-xxxxxxxxx,subnet-yyyyyyyyy" \
  --target-group-arns arn:aws:elasticloadbalancing:us-east-1:ACCOUNT_ID:targetgroup/tge-monitor-targets/xxxxxxxxx \
  --tags Key=Name,Value=TGE-Monitor-ASG,PropagateAtLaunch=true

# Create scaling policies
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name tge-monitor-asg \
  --policy-name scale-up \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ASGAverageCPUUtilization"
    },
    "TargetValue": 70.0
  }'
```

### Step 9: Verify Deployment

```bash
# Check system status
sudo systemctl status tge-api tge-worker nginx

# Check logs
sudo tail -f /var/log/tge-monitor/api-error.log

# Test API endpoint
curl https://yourdomain.com/health

# Test authentication
curl -X POST https://yourdomain.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}'

# Monitor CloudWatch logs
aws logs tail /tge-monitor/api/error --follow

# Check RDS connections
aws rds describe-db-instances --db-instance-identifier tge-monitor-db

# Check ElastiCache status
aws elasticache describe-replication-groups --replication-group-id tge-monitor-redis
```

## 🔒 Production Configuration

### Environment Variables Reference

```bash
# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
DATABASE_URL=postgresql://user:password@host:5432/database
DATABASE_POOL_SIZE=20                # Connection pool size
DATABASE_MAX_OVERFLOW=10             # Max connections beyond pool
DATABASE_POOL_TIMEOUT=30             # Connection timeout (seconds)
DATABASE_POOL_RECYCLE=3600          # Recycle connections after 1 hour
DATABASE_ECHO=false                  # Log SQL queries (set true for debug)

# ============================================================================
# REDIS CONFIGURATION
# ============================================================================
REDIS_URL=redis://:password@host:6379/0
REDIS_MAX_CONNECTIONS=50             # Max connection pool size
REDIS_SOCKET_TIMEOUT=5              # Socket timeout (seconds)
REDIS_SOCKET_CONNECT_TIMEOUT=5      # Connection timeout (seconds)
REDIS_RETRY_ON_TIMEOUT=true         # Retry on timeout
REDIS_HEALTH_CHECK_INTERVAL=30      # Health check interval (seconds)

# ============================================================================
# SECURITY CONFIGURATION
# ============================================================================
SECRET_KEY=                          # Generate with: openssl rand -hex 32
ADMIN_USERNAME=admin                 # Admin username
ADMIN_PASSWORD=                      # Generate with: openssl rand -base64 32
JWT_EXPIRATION_HOURS=24             # JWT token expiration
JWT_ALGORITHM=HS256                 # JWT signing algorithm
API_KEY_EXPIRATION_DAYS=90          # API key expiration
PASSWORD_MIN_LENGTH=12              # Minimum password length
PASSWORD_REQUIRE_SPECIAL=true       # Require special characters

# ============================================================================
# APPLICATION CONFIGURATION
# ============================================================================
ENV=production                       # Environment: development/production
DEBUG=false                          # Debug mode (never true in production!)
API_HOST=0.0.0.0                    # API bind address
API_PORT=8000                       # API port
API_WORKERS=4                       # Gunicorn worker processes
LOG_LEVEL=INFO                      # Logging: DEBUG/INFO/WARNING/ERROR
LOG_FORMAT=json                     # Log format: json/text
CORS_ORIGINS=https://yourdomain.com # Allowed CORS origins (comma-separated)
MAX_REQUEST_SIZE=10485760           # Max request size (10MB)
REQUEST_TIMEOUT=30                  # Request timeout (seconds)

# ============================================================================
# TWITTER API CONFIGURATION
# ============================================================================
TWITTER_BEARER_TOKEN=               # Twitter API bearer token
TWITTER_RATE_LIMIT=300             # Requests per window
TWITTER_RATE_WINDOW=900            # Rate limit window (seconds)
TWITTER_MAX_RESULTS=100            # Max results per request
TWITTER_TIMEOUT=30                 # Request timeout (seconds)
TWITTER_RETRY_ATTEMPTS=3           # Retry failed requests

# ============================================================================
# EMAIL CONFIGURATION
# ============================================================================
EMAIL_ENABLED=true                  # Enable email notifications
EMAIL_BACKEND=smtp                  # Backend: smtp/ses
EMAIL_USER=alerts@yourdomain.com   # SMTP username or SES sender
EMAIL_PASSWORD=                     # SMTP password or SES credentials
EMAIL_SMTP_HOST=smtp.gmail.com     # SMTP host
EMAIL_SMTP_PORT=587                # SMTP port
EMAIL_USE_TLS=true                 # Use TLS encryption
EMAIL_FROM=TGE Monitor <alerts@yourdomain.com>
EMAIL_RECIPIENTS=admin@yourdomain.com,team@yourdomain.com
EMAIL_RATE_LIMIT=10                # Max emails per hour
EMAIL_TEMPLATE_DIR=templates/email

# ============================================================================
# MONITORING CONFIGURATION
# ============================================================================
MONITORING_ENABLED=true             # Enable monitoring
MONITORING_INTERVAL=300            # Monitoring interval (seconds)
METRICS_RETENTION_DAYS=30          # Metrics retention period
HEALTH_CHECK_INTERVAL=60           # Health check interval
PROMETHEUS_PORT=9090               # Prometheus metrics port
GRAFANA_PORT=3000                  # Grafana dashboard port

# ============================================================================
# RATE LIMITING CONFIGURATION
# ============================================================================
RATE_LIMIT_ENABLED=true            # Enable rate limiting
RATE_LIMIT_STRATEGY=sliding_window # Strategy: fixed_window/sliding_window/token_bucket
RATE_LIMIT_API_GENERAL=1000:3600  # General API: requests:window_seconds
RATE_LIMIT_API_ALERTS=100:3600    # Alerts API: requests:window_seconds
RATE_LIMIT_WEBSOCKET=10:60        # WebSocket: connections:window_seconds
RATE_LIMIT_LOGIN_ATTEMPTS=5:300   # Login attempts: tries:lockout_seconds

# ============================================================================
# NEWS FEED CONFIGURATION
# ============================================================================
NEWS_FEEDS=https://theblock.co/rss.xml,https://decrypt.co/feed,https://cointelegraph.com/rss
NEWS_SCRAPE_INTERVAL=600           # Feed scrape interval (seconds)
NEWS_MAX_ARTICLES=100              # Max articles per feed
NEWS_TIMEOUT=30                    # Request timeout (seconds)
NEWS_USER_AGENT=TGE Monitor Bot/1.0

# ============================================================================
# WORKER CONFIGURATION
# ============================================================================
WORKER_PROCESSES=2                 # Number of background workers
WORKER_CONCURRENCY=10              # Concurrent tasks per worker
WORKER_MAX_TASKS=1000             # Max tasks before worker restart
WORKER_PREFETCH_MULTIPLIER=4      # Task prefetch multiplier

# ============================================================================
# CACHING CONFIGURATION
# ============================================================================
CACHE_ENABLED=true                 # Enable caching
CACHE_TTL=3600                    # Default cache TTL (seconds)
CACHE_ALERTS_TTL=300              # Alerts cache TTL
CACHE_COMPANIES_TTL=3600          # Companies cache TTL
CACHE_MAX_SIZE=1000               # Max cached items

# ============================================================================
# AWS CONFIGURATION
# ============================================================================
AWS_REGION=us-east-1              # AWS region
AWS_ACCESS_KEY_ID=                # AWS access key (prefer IAM role)
AWS_SECRET_ACCESS_KEY=            # AWS secret key (prefer IAM role)
AWS_S3_BUCKET=tge-monitor-backups # S3 bucket for backups
AWS_CLOUDWATCH_ENABLED=true       # Enable CloudWatch integration
AWS_SNS_TOPIC_ARN=                # SNS topic for alerts

# ============================================================================
# BACKUP CONFIGURATION
# ============================================================================
BACKUP_ENABLED=true                # Enable automated backups
BACKUP_INTERVAL=86400             # Backup interval (seconds)
BACKUP_RETENTION_DAYS=30          # Backup retention period
BACKUP_S3_BUCKET=tge-monitor-backups
BACKUP_S3_PREFIX=database/        # S3 prefix for backups

# ============================================================================
# FEATURE FLAGS
# ============================================================================
FEATURE_WEBSOCKET_ENABLED=true    # Enable WebSocket support
FEATURE_EMAIL_ALERTS=true         # Enable email alerts
FEATURE_TWITTER_MONITORING=true   # Enable Twitter monitoring
FEATURE_NEWS_MONITORING=true      # Enable news monitoring
FEATURE_ML_ANALYSIS=true          # Enable ML content analysis
FEATURE_RATE_LIMITING=true        # Enable rate limiting
FEATURE_METRICS=true              # Enable metrics collection
```

## 🔐 API Reference

### Authentication

#### POST /auth/login
Login and obtain JWT token

**Request:**
```bash
curl -X POST https://yourdomain.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your_password"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

#### POST /auth/register
Register new user (requires admin privileges)

**Request:**
```bash
curl -X POST https://yourdomain.com/auth/register \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }'
```

#### POST /auth/api-keys
Create new API key

**Request:**
```bash
curl -X POST https://yourdomain.com/auth/api-keys \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production API Key",
    "expires_in_days": 90
  }'
```

**Response:**
```json
{
  "id": 1,
  "name": "Production API Key",
  "key": "tge_xxxxxxxxxxxxxxxxxxxxxxxx",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "expires_at": "2024-04-15T10:30:00Z"
}
```

### Companies

#### GET /companies
List all companies with filtering

**Request:**
```bash
curl -X GET "https://yourdomain.com/companies?priority=HIGH&limit=10" \
  -H "X-API-Key: YOUR_API_KEY"
```

**Query Parameters:**
- `priority`: Filter by priority (HIGH/MEDIUM/LOW)
- `status`: Filter by status (active/inactive)
- `has_tokens`: Filter companies with tokens (true/false)
- `limit`: Maximum results (default: 100, max: 1000)
- `offset`: Pagination offset (default: 0)

**Response:**
```json
[
  {
    "id": 1,
    "name": "Caldera",
    "aliases": ["Caldera Labs", "Caldera Protocol"],
    "tokens": ["CAL"],
    "priority": "HIGH",
    "status": "active",
    "website": "https://caldera.xyz",
    "twitter_handle": "@Caldera",
    "description": "L2 Blockchain Platform",
    "exclusions": ["testnet", "demo"],
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

#### POST /companies
Create new company (admin only)

**Request:**
```bash
curl -X POST https://yourdomain.com/companies \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Protocol",
    "aliases": ["New Protocol Labs"],
    "tokens": ["NEW"],
    "priority": "HIGH",
    "status": "active",
    "website": "https://newprotocol.xyz",
    "twitter_handle": "@NewProtocol",
    "description": "Next-gen blockchain"
  }'
```

### Alerts

#### GET /alerts
Get alerts with advanced filtering

**Request:**
```bash
curl -X GET "https://yourdomain.com/alerts?min_confidence=0.7&urgency_level=high&limit=20" \
  -H "X-API-Key: YOUR_API_KEY"
```

**Query Parameters:**
- `company_id`: Filter by company ID
- `source`: Filter by source (twitter/news/manual)
- `min_confidence`: Minimum confidence score (0.0-1.0)
- `max_confidence`: Maximum confidence score (0.0-1.0)
- `urgency_level`: Filter by urgency (low/medium/high/critical)
- `status`: Filter by status (active/archived/false_positive)
- `from_date`: Start date (ISO 8601)
- `to_date`: End date (ISO 8601)
- `keywords`: Filter by keywords (comma-separated)
- `limit`: Maximum results (default: 100, max: 1000)
- `offset`: Pagination offset

**Response:**
```json
[
  {
    "id": 123,
    "title": "Caldera TGE Announcement - Token Launch on Jan 20",
    "content": "Caldera announces their Token Generation Event...",
    "source": "twitter",
    "source_url": "https://twitter.com/Caldera/status/...",
    "confidence": 0.92,
    "company_id": 1,
    "company": {
      "id": 1,
      "name": "Caldera",
      "tokens": ["CAL"]
    },
    "keywords_matched": ["TGE", "token launch", "airdrop"],
    "tokens_mentioned": ["$CAL"],
    "analysis_data": {
      "sentiment": "positive",
      "key_phrases": ["token generation", "live now"],
      "urgency_indicators": ["today", "now live"]
    },
    "sentiment_score": 0.85,
    "urgency_level": "high",
    "status": "active",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

#### POST /alerts
Create manual alert

```bash
curl -X POST https://yourdomain.com/alerts \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Manual Alert",
    "content": "Important TGE information",
    "source": "manual",
    "confidence": 0.9,
    "company_id": 1,
    "urgency_level": "high"
  }'
```

#### PUT /alerts/{id}
Update alert status

```bash
curl -X PUT https://yourdomain.com/alerts/123 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "archived",
    "urgency_level": "medium"
  }'
```

#### POST /alerts/bulk-update
Bulk update alerts

```bash
curl -X POST https://yourdomain.com/alerts/bulk-update \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "alert_ids": [123, 124, 125],
    "status": "archived"
  }'
```

### Statistics

#### GET /statistics/alerts
Get alert statistics

**Request:**
```bash
curl -X GET "https://yourdomain.com/statistics/alerts?days=7" \
  -H "X-API-Key: YOUR_API_KEY"
```

**Response:**
```json
{
  "total_alerts": 1250,
  "alerts_by_source": {
    "twitter": 800,
    "news": 400,
    "manual": 50
  },
  "alerts_by_confidence": {
    "high": 450,
    "medium": 600,
    "low": 200
  },
  "alerts_by_urgency": {
    "critical": 50,
    "high": 300,
    "medium": 700,
    "low": 200
  },
  "alerts_by_company": {
    "Caldera": 150,
    "Fabric": 120,
    "Other": 980
  },
  "recent_trend": {
    "2024-01-14": 180,
    "2024-01-15": 195,
    "2024-01-16": 170
  }
}
```

#### GET /statistics/system
Get system statistics

**Response:**
```json
{
  "total_companies": 50,
  "total_feeds": 15,
  "active_feeds": 14,
  "total_alerts": 5000,
  "alerts_last_24h": 180,
  "alerts_last_7d": 1250,
  "avg_confidence": 0.72,
  "system_uptime": 99.98,
  "last_monitoring_session": "2024-01-15T10:00:00Z"
}
```

### Health & Monitoring

#### GET /health
System health check

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "database": true,
  "redis": true,
  "feeds_health": {
    "active": 14,
    "inactive": 1,
    "error_rate": 0.02
  },
  "system_metrics": {
    "cpu_percent": 45.2,
    "memory_percent": 62.5,
    "disk_percent": 35.8
  }
}
```

### WebSocket API

#### Connect to WebSocket
```javascript
const ws = new WebSocket('wss://yourdomain.com/ws');

// Authenticate
ws.send(JSON.stringify({
  type: 'auth',
  data: { token: 'YOUR_JWT_TOKEN' }
}));

// Subscribe to alerts
ws.send(JSON.stringify({
  type: 'subscribe',
  data: {
    type: 'all_alerts',
    filters: {
      confidence_threshold: 0.7,
      urgency_levels: ['high', 'critical'],
      companies: [1, 2, 3]
    }
  }
}));

// Handle messages
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);

  if (message.type === 'alert') {
    // Handle new alert
    console.log('New alert:', message.data);
  }
};
```

**Message Types:**
- `auth` - Authentication request/response
- `subscribe` - Subscribe to alerts
- `unsubscribe` - Unsubscribe from alerts
- `alert` - New alert notification
- `status` - Connection status update
- `ping/pong` - Keep-alive messages
- `error` - Error messages

## 📊 Monitoring & Logging

### Application Logs

**Log Locations:**
- API logs: `/var/log/tge-monitor/api-access.log`, `api-error.log`
- Worker logs: `/var/log/tge-monitor/worker.log`
- Nginx logs: `/var/log/nginx/tge-monitor-access.log`, `error.log`
- System logs: `journalctl -u tge-api -u tge-worker`

**View Logs:**
```bash
# Real-time API logs
sudo tail -f /var/log/tge-monitor/api-error.log

# Real-time all services
sudo journalctl -u tge-api -u tge-worker -f

# Filter by level
sudo journalctl -u tge-api -p err -f

# Last 100 lines
sudo journalctl -u tge-api -n 100
```

### Prometheus Metrics

**Metrics Endpoint:** `https://yourdomain.com/metrics`

**Available Metrics:**
- `tge_api_requests_total` - Total API requests
- `tge_api_request_duration_seconds` - Request duration histogram
- `tge_api_errors_total` - API error counter
- `tge_alerts_created_total` - Alerts created counter
- `tge_twitter_requests_total` - Twitter API requests
- `tge_database_connections` - Active database connections
- `tge_cache_hits_total` - Cache hit counter
- `tge_cache_misses_total` - Cache miss counter

**Query Examples:**
```promql
# Request rate (per second)
rate(tge_api_requests_total[5m])

# Error rate
rate(tge_api_errors_total[5m]) / rate(tge_api_requests_total[5m])

# P95 latency
histogram_quantile(0.95, rate(tge_api_request_duration_seconds_bucket[5m]))

# Cache hit rate
rate(tge_cache_hits_total[5m]) / (rate(tge_cache_hits_total[5m]) + rate(tge_cache_misses_total[5m]))
```

### Grafana Dashboards

**Access:** `https://yourdomain.com:3000`

**Pre-built Dashboards:**
1. **System Overview** - CPU, memory, disk, network
2. **API Performance** - Request rates, latency, errors
3. **Database Metrics** - Connections, queries, performance
4. **Alert Analytics** - Alert trends, confidence distribution
5. **Twitter Monitoring** - API usage, rate limits

**Import Dashboard:**
```bash
# Use dashboard ID from https://grafana.com/grafana/dashboards/
# Or import JSON from /dashboards/ directory
```

### CloudWatch Integration

**Log Groups:**
- `/tge-monitor/api/access`
- `/tge-monitor/api/error`
- `/tge-monitor/worker`
- `/tge-monitor/nginx/access`

**Metrics Namespace:** `TGEMonitor`

**Custom Metrics:**
- `CPU_IDLE`, `CPU_IOWAIT`
- `MEM_USED`
- `DISK_USED`
- `TCP_CONNECTIONS`

**View Logs:**
```bash
# Tail logs
aws logs tail /tge-monitor/api/error --follow

# Filter by pattern
aws logs filter-log-events \
  --log-group-name /tge-monitor/api/error \
  --filter-pattern "ERROR"

# Query with Insights
aws logs start-query \
  --log-group-name /tge-monitor/api/error \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 20'
```

## 🛡️ Security

### Security Best Practices

1. **Use Strong Passwords**
   ```bash
   # Generate secure password
   openssl rand -base64 32

   # Generate secret key
   openssl rand -hex 32
   ```

2. **Enable HTTPS/TLS**
   - Use Let's Encrypt for free SSL certificates
   - Enable HSTS headers
   - Use TLS 1.2 or higher

3. **Secure Environment Variables**
   ```bash
   # Restrict .env file permissions
   chmod 600 /opt/tge-monitor/.env
   chown tge-monitor:tge-monitor /opt/tge-monitor/.env
   ```

4. **Enable Rate Limiting**
   - Configure appropriate limits for each endpoint
   - Use Redis for distributed rate limiting
   - Monitor and adjust based on traffic patterns

5. **Regular Security Updates**
   ```bash
   # Update system packages
   sudo apt update && sudo apt upgrade -y

   # Update Python dependencies
   pip install --upgrade -r requirements.txt

   # Audit dependencies
   pip-audit
   ```

6. **Database Security**
   - Use strong passwords
   - Enable SSL/TLS for connections
   - Limit network access with security groups
   - Regular backups with encryption
   - Enable audit logging

7. **API Security**
   - Validate all inputs
   - Use parameterized queries (SQLAlchemy ORM)
   - Implement CORS properly
   - Use API keys with expiration
   - Log security events

8. **Network Security**
   - Use AWS security groups
   - Implement VPC with private subnets
   - Use bastion hosts for SSH access
   - Enable VPC Flow Logs
   - Use AWS WAF for additional protection

### Security Checklist

- [ ] Change all default passwords
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Configure firewall rules (security groups)
- [ ] Enable database encryption at rest
- [ ] Enable database encryption in transit
- [ ] Set up automated backups
- [ ] Configure rate limiting
- [ ] Enable audit logging
- [ ] Set up security monitoring and alerts
- [ ] Implement least privilege IAM policies
- [ ] Enable MFA for admin accounts
- [ ] Regular security audits
- [ ] Keep dependencies updated
- [ ] Review and rotate API keys regularly

## ⚡ Performance Optimization

### Database Optimization

```sql
-- Add indexes for frequent queries
CREATE INDEX idx_alerts_company_confidence ON alerts(company_id, confidence);
CREATE INDEX idx_alerts_created_status ON alerts(created_at, status);
CREATE INDEX idx_alerts_source_urgency ON alerts(source, urgency_level);

-- Analyze query performance
EXPLAIN ANALYZE
SELECT * FROM alerts
WHERE confidence > 0.7 AND status = 'active'
ORDER BY created_at DESC LIMIT 100;

-- Update statistics
ANALYZE;

-- Vacuum database
VACUUM ANALYZE;
```

### Redis Optimization

```bash
# Configure maxmemory policy
redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Monitor memory usage
redis-cli INFO memory

# Check slow queries
redis-cli SLOWLOG GET 10

# Benchmark performance
redis-benchmark -t set,get -n 100000 -q
```

### Application Optimization

```python
# Use connection pooling
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Enable query result caching
CACHE_ENABLED=true
CACHE_TTL=3600

# Optimize worker configuration
WORKER_PROCESSES=4
WORKER_CONCURRENCY=10
```

### Nginx Optimization

```nginx
# Enable gzip compression
gzip on;
gzip_vary on;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

# Enable HTTP/2
listen 443 ssl http2;

# Configure caching
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=1g inactive=60m;

# Enable keep-alive
keepalive_timeout 65;
keepalive_requests 100;
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Database Connection Errors

**Symptoms:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solutions:**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check connection parameters
psql -h localhost -U tge_user -d tge_monitor

# Verify pg_hba.conf allows connections
sudo nano /etc/postgresql/15/main/pg_hba.conf

# Check listen_addresses in postgresql.conf
sudo nano /etc/postgresql/15/main/postgresql.conf

# Restart PostgreSQL
sudo systemctl restart postgresql
```

#### 2. Redis Connection Errors

**Symptoms:**
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**Solutions:**
```bash
# Check Redis status
sudo systemctl status redis

# Test connection
redis-cli ping

# Check Redis configuration
sudo nano /etc/redis/redis.conf

# Verify bind address and password
redis-cli -a your_password ping

# Restart Redis
sudo systemctl restart redis
```

#### 3. High Memory Usage

**Symptoms:**
- System becomes slow
- OOM killer terminates processes

**Solutions:**
```bash
# Check memory usage
free -h
top -o %MEM

# Check application memory
ps aux | grep python | awk '{print $4, $11}' | sort -rn

# Restart services to clear memory
sudo systemctl restart tge-api tge-worker

# Optimize database pool
# Reduce DATABASE_POOL_SIZE in .env

# Clear Redis cache
redis-cli FLUSHDB
```

#### 4. High CPU Usage

**Solutions:**
```bash
# Identify CPU-intensive processes
top -o %CPU

# Check API workers
ps aux | grep gunicorn

# Reduce worker processes if needed
# Edit /etc/systemd/system/tge-api.service
# Change -w 4 to -w 2

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart tge-api
```

#### 5. API Authentication Failures

**Symptoms:**
```json
{"detail": "Could not validate credentials"}
```

**Solutions:**
```bash
# Verify JWT secret key
grep SECRET_KEY /opt/tge-monitor/.env

# Check token expiration
# Use https://jwt.io to decode token

# Create new admin user
python -c "
import asyncio
from src.auth import create_admin_user_if_not_exists
from src.database import DatabaseManager

async def reset():
    async for db in DatabaseManager.get_db():
        await create_admin_user_if_not_exists(db)
        break

asyncio.run(reset())
"
```

#### 6. WebSocket Connection Issues

**Solutions:**
```bash
# Check nginx WebSocket configuration
sudo nginx -t

# Verify WebSocket endpoint
wscat -c wss://yourdomain.com/ws

# Check logs
sudo tail -f /var/log/nginx/error.log
sudo journalctl -u tge-api -f | grep -i websocket
```

#### 7. Rate Limiting Issues

**Solutions:**
```bash
# Check current limits
redis-cli KEYS "rate_limit:*"

# Reset rate limits for specific user
redis-cli DEL "rate_limit:user:123"

# Adjust limits in .env
RATE_LIMIT_API_GENERAL=2000:3600

# Restart services
sudo systemctl restart tge-api
```

### Debug Mode

```bash
# Enable debug logging
# Edit .env
LOG_LEVEL=DEBUG
DEBUG=true

# Restart services
sudo systemctl restart tge-api tge-worker

# View debug logs
sudo journalctl -u tge-api -f

# Disable debug mode after troubleshooting
LOG_LEVEL=INFO
DEBUG=false
```

### Performance Diagnostics

```bash
# Check API response times
curl -w "@curl-format.txt" -o /dev/null -s https://yourdomain.com/health

# Database query performance
psql -U tge_user -d tge_monitor -c "
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
"

# Redis performance
redis-cli --latency

# System resource usage
htop
iotop
```

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork the repository**
```bash
git clone https://github.com/yourusername/OCL_Twitter_Scraper.git
cd OCL_Twitter_Scraper
git checkout -b feature/your-feature-name
```

2. **Create virtual environment**
```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

3. **Make your changes**
- Follow PEP 8 style guide
- Add tests for new features
- Update documentation

4. **Run tests**
```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Run linting
flake8 src/ tests/
black src/ tests/
mypy src/
```

5. **Submit pull request**
- Ensure all tests pass
- Update CHANGELOG.md
- Provide clear description

## 📄 License

This project is licensed under the MIT License - see [LICENSE.md](LICENSE.md) for details.

## 🙏 Acknowledgments

- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - Powerful ORM
- **PostgreSQL** - Robust database
- **Redis** - High-performance cache
- **Docker** - Containerization
- **AWS** - Cloud infrastructure
- **Prometheus & Grafana** - Monitoring

---

## 📞 Support

- **Documentation**: [https://docs.yourdomain.com](https://docs.yourdomain.com)
- **Issues**: [GitHub Issues](https://github.com/yourusername/OCL_Twitter_Scraper/issues)
- **Email**: support@yourdomain.com
- **Discord**: [Join our community](https://discord.gg/yourinvite)

---

**Enhanced TGE Monitor System** - Production-ready cryptocurrency token generation event monitoring with real-time alerts, comprehensive API, and enterprise-grade infrastructure.

Built with ❤️ for the crypto community.
