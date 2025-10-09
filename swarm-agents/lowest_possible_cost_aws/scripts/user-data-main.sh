#!/bin/bash
# User Data Script for Ultra-Low-Cost TGE Swarm Main Instance
# Cost Optimization Engineer: Claude

set -e

# Variables from Terraform
REGION="${region}"
AUTO_SHUTDOWN_ENABLED="${auto_shutdown_enabled}"
AUTO_SHUTDOWN_SCHEDULE="${auto_shutdown_schedule}"
AUTO_STARTUP_SCHEDULE="${auto_startup_schedule}"

# Log everything
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "Starting TGE Swarm Cost-Optimized Instance Setup..."
echo "Region: $REGION"
echo "Auto-shutdown enabled: $AUTO_SHUTDOWN_ENABLED"

# Update system
yum update -y

# Install required packages
yum install -y \
    docker \
    docker-compose \
    git \
    curl \
    wget \
    htop \
    aws-cli \
    amazon-cloudwatch-agent \
    cronie

# Start and enable Docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose v2
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# Create application directory
mkdir -p /opt/tge-swarm
cd /opt/tge-swarm

# Clone the repository (assuming it's accessible)
# Note: In production, you'd copy from S3 or use a private repo
git clone https://github.com/your-org/TGE-Swarm.git . || echo "Repository clone failed, using pre-built image"

# Create necessary directories
mkdir -p logs backups safla-memory config reports

# Copy config.py to appropriate locations for TGE monitoring
if [ -f "/opt/tge-swarm/config.py" ]; then
    cp /opt/tge-swarm/config.py /opt/tge-swarm/swarm-agents/
    cp /opt/tge-swarm/config.py /opt/tge-swarm/config/
    echo "config.py integrated for TGE monitoring"
else
    echo "Warning: config.py not found in repository root"
fi

# Install Python dependencies for config.py
yum install -y python3-pip
pip3 install python-dotenv

# Create .env file for TGE configuration
cat > /opt/tge-swarm/config/.env << 'EOF'
# TGE Monitoring Configuration
LOG_LEVEL=INFO
LOG_FILE=/opt/tge-swarm/logs/tge_monitor.log

# Email Configuration (configure via Parameter Store)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=${email_user:-}
EMAIL_PASSWORD=${email_password:-}
RECIPIENT_EMAIL=${recipient_email:-admin@company.com}

# Twitter Configuration (configure via Parameter Store)
TWITTER_BEARER_TOKEN=${twitter_bearer_token:-}

# AWS Integration for cost-optimized deployment
AWS_REGION=${region}
ENVIRONMENT=cost-optimized
EOF

# Copy .env to multiple locations for compatibility
cp /opt/tge-swarm/config/.env /opt/tge-swarm/
cp /opt/tge-swarm/config/.env /opt/tge-swarm/swarm-agents/

# Set up spot instance interruption handling
cat > /opt/tge-swarm/spot-interruption-handler.sh << 'EOF'
#!/bin/bash
# Spot Instance Interruption Handler

METADATA_TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
SPOT_ACTION=$(curl -s -H "X-aws-ec2-metadata-token: $METADATA_TOKEN" http://169.254.169.254/latest/meta-data/spot/instance-action 2>/dev/null)

if [ $? -eq 0 ] && [ -n "$SPOT_ACTION" ]; then
    echo "$(date): Spot interruption detected: $SPOT_ACTION"
    
    # Send alert
    aws sns publish --region $REGION \
        --topic-arn $(aws ssm get-parameter --name "/tge-swarm/sns-topic-arn" --query "Parameter.Value" --output text) \
        --message "Spot instance interruption detected. Gracefully shutting down TGE Swarm services." \
        --subject "TGE Swarm Spot Interruption Alert"
    
    # Graceful shutdown
    echo "$(date): Starting graceful shutdown..."
    cd /opt/tge-swarm
    
    # Create backup before shutdown
    ./scripts/backup-before-interruption.sh
    
    # Stop services gracefully
    docker-compose -f docker/docker-compose-cost-optimized.yml down --timeout 60
    
    echo "$(date): Graceful shutdown completed"
else
    echo "$(date): No spot interruption detected"
fi
EOF

chmod +x /opt/tge-swarm/spot-interruption-handler.sh

# Set up backup script for interruptions
cat > /opt/tge-swarm/scripts/backup-before-interruption.sh << 'EOF'
#!/bin/bash
# Emergency backup before spot interruption

BACKUP_DIR="/opt/tge-swarm/backups/emergency-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Creating emergency backup in $BACKUP_DIR"

# Backup database
docker exec tge-postgres-cost-optimized pg_dump -U swarm_user tge_swarm > "$BACKUP_DIR/database.sql"

# Backup Redis data
docker exec tge-redis-cost-optimized redis-cli --rdb "$BACKUP_DIR/redis-dump.rdb"

# Backup application data
cp -r /opt/tge-swarm/safla-memory "$BACKUP_DIR/"
cp -r /opt/tge-swarm/logs "$BACKUP_DIR/"

# Compress backup
tar -czf "$BACKUP_DIR.tar.gz" -C "$BACKUP_DIR" .
rm -rf "$BACKUP_DIR"

# Upload to S3 if configured
if [ -n "$BACKUP_S3_BUCKET" ]; then
    aws s3 cp "$BACKUP_DIR.tar.gz" "s3://$BACKUP_S3_BUCKET/emergency-backups/"
fi

echo "Emergency backup completed: $BACKUP_DIR.tar.gz"
EOF

chmod +x /opt/tge-swarm/scripts/backup-before-interruption.sh

# Set up cron job for spot interruption monitoring
echo "*/1 * * * * root /opt/tge-swarm/spot-interruption-handler.sh >> /var/log/spot-monitor.log 2>&1" >> /etc/crontab

# Set up auto-shutdown/startup if enabled
if [ "$AUTO_SHUTDOWN_ENABLED" = "true" ]; then
    cat > /opt/tge-swarm/auto-shutdown.sh << 'EOF'
#!/bin/bash
# Auto-shutdown script for cost optimization

echo "$(date): Auto-shutdown initiated"

# Send notification
aws sns publish --region $REGION \
    --topic-arn $(aws ssm get-parameter --name "/tge-swarm/sns-topic-arn" --query "Parameter.Value" --output text) \
    --message "TGE Swarm auto-shutdown initiated for cost optimization" \
    --subject "TGE Swarm Auto-Shutdown"

# Stop services
cd /opt/tge-swarm
docker-compose -f docker/docker-compose-cost-optimized.yml down

# Stop instance
sudo shutdown -h now
EOF

    chmod +x /opt/tge-swarm/auto-shutdown.sh
    
    # Add to crontab
    echo "$AUTO_SHUTDOWN_SCHEDULE root /opt/tge-swarm/auto-shutdown.sh" >> /etc/crontab
fi

# Install CloudWatch agent configuration
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
{
    "metrics": {
        "namespace": "TGE-Swarm/CostOptimized",
        "metrics_collected": {
            "cpu": {
                "measurement": ["cpu_usage_idle", "cpu_usage_iowait", "cpu_usage_user", "cpu_usage_system"],
                "metrics_collection_interval": 300
            },
            "disk": {
                "measurement": ["used_percent"],
                "metrics_collection_interval": 300,
                "resources": ["*"]
            },
            "mem": {
                "measurement": ["mem_used_percent"],
                "metrics_collection_interval": 300
            }
        }
    },
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/opt/tge-swarm/logs/*.log",
                        "log_group_name": "/tge-swarm/application",
                        "log_stream_name": "{instance_id}/application"
                    },
                    {
                        "file_path": "/var/log/spot-monitor.log",
                        "log_group_name": "/tge-swarm/spot-monitoring",
                        "log_stream_name": "{instance_id}/spot-monitoring"
                    }
                ]
            }
        }
    }
}
EOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -s \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

# Create systemd service for TGE Swarm
cat > /etc/systemd/system/tge-swarm.service << 'EOF'
[Unit]
Description=TGE Swarm Cost-Optimized Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/tge-swarm
ExecStart=/usr/local/bin/docker-compose -f docker/docker-compose-cost-optimized.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker/docker-compose-cost-optimized.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
systemctl daemon-reload
systemctl enable tge-swarm.service

# Set up log rotation
cat > /etc/logrotate.d/tge-swarm << 'EOF'
/opt/tge-swarm/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    maxsize 100M
}
EOF

# Create health check script
cat > /opt/tge-swarm/health-check.sh << 'EOF'
#!/bin/bash
# System health check for cost monitoring

# Check if main services are running
if ! docker ps | grep -q "tge-swarm-all-in-one"; then
    echo "ERROR: Main TGE Swarm container not running"
    exit 1
fi

if ! docker ps | grep -q "tge-postgres-cost-optimized"; then
    echo "ERROR: PostgreSQL container not running"
    exit 1
fi

# Check API health
if ! curl -f http://localhost:8080/health >/dev/null 2>&1; then
    echo "ERROR: TGE Swarm API not responding"
    exit 1
fi

echo "All services healthy"
exit 0
EOF

chmod +x /opt/tge-swarm/health-check.sh

# Start TGE Swarm services
cd /opt/tge-swarm
systemctl start tge-swarm.service

# Create a startup completion marker
touch /opt/tge-swarm/startup-complete

echo "TGE Swarm Cost-Optimized Instance Setup Complete!"
echo "Services starting up... Check logs in /opt/tge-swarm/logs/"