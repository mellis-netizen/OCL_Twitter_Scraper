#!/bin/bash
# TGE Swarm Queen User Data Script
# Automated setup and configuration for the Swarm Queen Orchestrator

set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

# Variables
ENVIRONMENT="${environment}"
POSTGRES_ENDPOINT="${postgres_endpoint}"
REDIS_ENDPOINT="${redis_endpoint}"
CONSUL_ENDPOINT="${consul_endpoint}"

# Update system
yum update -y

# Install required packages
yum install -y \
    docker \
    git \
    python3 \
    python3-pip \
    htop \
    curl \
    wget \
    unzip \
    jq \
    awscli \
    amazon-cloudwatch-agent

# Start and enable Docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

# Create application directories
mkdir -p /opt/tge-swarm/{config,logs,data,backups}
mkdir -p /app/{src,config,logs,reports,safla-memory}

# Mount EBS volume for data
if [ ! -d "/app/data" ]; then
    mkdir -p /app/data
fi

# Check if volume is already formatted
if ! blkid /dev/xvdf; then
    mkfs.ext4 /dev/xvdf
fi

# Mount the volume
mount /dev/xvdf /app/data
echo '/dev/xvdf /app/data ext4 defaults,nofail 0 2' >> /etc/fstab

# Set up CloudWatch agent
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
{
    "agent": {
        "metrics_collection_interval": 60,
        "run_as_user": "cwagent"
    },
    "metrics": {
        "namespace": "TGE/Swarm/Queen",
        "metrics_collected": {
            "cpu": {
                "measurement": [
                    "cpu_usage_idle",
                    "cpu_usage_iowait",
                    "cpu_usage_user",
                    "cpu_usage_system"
                ],
                "metrics_collection_interval": 60,
                "totalcpu": false
            },
            "disk": {
                "measurement": [
                    "used_percent"
                ],
                "metrics_collection_interval": 60,
                "resources": [
                    "*"
                ]
            },
            "mem": {
                "measurement": [
                    "mem_used_percent"
                ],
                "metrics_collection_interval": 60
            }
        }
    },
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/app/logs/queen.log",
                        "log_group_name": "/aws/ec2/swarm-queen",
                        "log_stream_name": "{instance_id}/queen"
                    },
                    {
                        "file_path": "/var/log/user-data.log",
                        "log_group_name": "/aws/ec2/swarm-queen",
                        "log_stream_name": "{instance_id}/user-data"
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
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
    -s

# Clone TGE Swarm repository
cd /opt/tge-swarm
git clone https://github.com/your-org/tge-swarm.git .

# Copy the root config.py to the swarm-agents directory
cp /opt/tge-swarm/config.py /opt/tge-swarm/swarm-agents/
cp /opt/tge-swarm/config.py /app/config/

# Install Python dependencies
cd /opt/tge-swarm/swarm-agents
pip3 install -r requirements.txt

# Install additional dependencies for config.py
pip3 install python-dotenv

# Create .env file for config.py settings
cat > /app/config/.env << 'EOF'
# TGE Monitoring Configuration
LOG_LEVEL=INFO
LOG_FILE=/app/logs/tge_monitor.log

# Email Configuration (optional - configure via AWS Parameter Store)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=${email_user:-}
EMAIL_PASSWORD=${email_password:-}
RECIPIENT_EMAIL=${recipient_email:-admin@company.com}

# Twitter Configuration (optional - configure via AWS Parameter Store)
TWITTER_BEARER_TOKEN=${twitter_bearer_token:-}

# AWS Integration
AWS_REGION=${AWS::Region}
ENVIRONMENT=${environment}
EOF

# Copy .env to multiple locations for compatibility
cp /app/config/.env /opt/tge-swarm/
cp /app/config/.env /opt/tge-swarm/swarm-agents/

# Create configuration files
cat > /app/config/swarm-config.yaml << EOF
environment: ${ENVIRONMENT}
services:
  postgres:
    endpoint: ${POSTGRES_ENDPOINT}
    database: tge_swarm
    username: swarm_user
  redis:
    endpoint: ${REDIS_ENDPOINT}
    cluster_mode: true
  consul:
    endpoint: ${CONSUL_ENDPOINT}
    port: 8500

queen:
  api_port: 8080
  metrics_port: 8001
  log_level: INFO
  max_workers: 10
  memory_limit: 2G

monitoring:
  prometheus_enabled: true
  grafana_enabled: true
  jaeger_enabled: true
  
logging:
  level: INFO
  format: json
  output: /app/logs/queen.log
EOF

# Create systemd service for Swarm Queen
cat > /etc/systemd/system/tge-swarm-queen.service << 'EOF'
[Unit]
Description=TGE Swarm Queen Orchestrator
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/tge-swarm/swarm-agents
Environment=PYTHONPATH=/opt/tge-swarm/swarm-agents:/opt/tge-swarm
Environment=CONFIG_PATH=/app/config/swarm-config.yaml
Environment=LOG_LEVEL=INFO
Environment=METRICS_PORT=8001
Environment=QUEEN_API_PORT=8080
EnvironmentFile=/app/config/.env
ExecStart=/usr/bin/python3 tge-queen-orchestrator.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Set up log rotation
cat > /etc/logrotate.d/tge-swarm << 'EOF'
/app/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 ec2-user ec2-user
    postrotate
        systemctl reload tge-swarm-queen || true
    endscript
}
EOF

# Create health check script
cat > /app/health-check.sh << 'EOF'
#!/bin/bash
# Health check script for Swarm Queen

HEALTH_URL="http://localhost:8080/health"
TIMEOUT=10

# Check if service is responding
if curl -f -s --max-time $TIMEOUT $HEALTH_URL > /dev/null; then
    echo "HEALTHY: Queen API is responding"
    exit 0
else
    echo "UNHEALTHY: Queen API is not responding"
    exit 1
fi
EOF

chmod +x /app/health-check.sh

# Set up cron job for health checks
echo "*/5 * * * * ec2-user /app/health-check.sh >> /app/logs/health.log 2>&1" >> /var/spool/cron/ec2-user

# Install monitoring tools
pip3 install prometheus-client

# Create backup script
cat > /app/backup.sh << 'EOF'
#!/bin/bash
# Backup script for Swarm Queen data

BACKUP_DIR="/app/backups"
S3_BUCKET="your-backup-bucket"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup configuration
tar -czf $BACKUP_DIR/config_$DATE.tar.gz /app/config/

# Backup logs
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz /app/logs/

# Backup memory data
tar -czf $BACKUP_DIR/memory_$DATE.tar.gz /app/safla-memory/

# Upload to S3
aws s3 cp $BACKUP_DIR/ s3://$S3_BUCKET/queen/ --recursive

# Clean up old backups (keep 7 days)
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x /app/backup.sh

# Schedule daily backups
echo "0 2 * * * ec2-user /app/backup.sh >> /app/logs/backup.log 2>&1" >> /var/spool/cron/ec2-user

# Set proper ownership
chown -R ec2-user:ec2-user /app/
chown -R ec2-user:ec2-user /opt/tge-swarm/

# Enable and start services
systemctl daemon-reload
systemctl enable tge-swarm-queen
systemctl start tge-swarm-queen

# Install security updates
yum update -y --security

# Configure firewall
if command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=8080/tcp
    firewall-cmd --permanent --add-port=8001/tcp
    firewall-cmd --reload
fi

# Signal that instance is ready
/opt/aws/bin/cfn-signal -e $? --stack ${AWS::StackName} --resource SwarmQueen --region ${AWS::Region} || true

echo "Swarm Queen setup completed successfully"