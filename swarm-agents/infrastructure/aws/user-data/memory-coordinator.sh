#!/bin/bash
# TGE Memory Coordinator User Data Script
# Automated setup and configuration for the Memory Coordinator

set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

# Variables
ENVIRONMENT="${environment}"
POSTGRES_ENDPOINT="${postgres_endpoint}"
REDIS_ENDPOINT="${redis_endpoint}"
QUEEN_ENDPOINT="${queen_endpoint}"

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

# Create application directories
mkdir -p /opt/tge-swarm/{config,logs,data,backups}
mkdir -p /app/{config,logs,reports,safla-memory}

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
        "namespace": "TGE/Swarm/Coordinator",
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
                        "file_path": "/app/logs/coordinator.log",
                        "log_group_name": "/aws/ec2/memory-coordinator",
                        "log_stream_name": "{instance_id}/coordinator"
                    },
                    {
                        "file_path": "/var/log/user-data.log",
                        "log_group_name": "/aws/ec2/memory-coordinator",
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

# Install Python dependencies
cd /opt/tge-swarm/swarm-agents
pip3 install -r requirements.txt

# Create configuration files
cat > /app/config/coordinator-config.yaml << EOF
environment: ${ENVIRONMENT}
services:
  postgres:
    endpoint: ${POSTGRES_ENDPOINT}
    database: tge_swarm
    username: swarm_user
  redis:
    endpoint: ${REDIS_ENDPOINT}
    cluster_mode: true
  queen:
    endpoint: ${QUEEN_ENDPOINT}
    port: 8080

coordinator:
  api_port: 8002
  sync_interval: 90
  memory_path: /app/safla-memory
  log_level: INFO
  max_memory_size: 1G

monitoring:
  prometheus_enabled: true
  metrics_port: 8003
  
logging:
  level: INFO
  format: json
  output: /app/logs/coordinator.log
EOF

# Create systemd service for Memory Coordinator
cat > /etc/systemd/system/tge-memory-coordinator.service << 'EOF'
[Unit]
Description=TGE Memory Coordinator
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/tge-swarm/swarm-agents
Environment=PYTHONPATH=/opt/tge-swarm/swarm-agents
Environment=CONFIG_PATH=/app/config/coordinator-config.yaml
Environment=LOG_LEVEL=INFO
Environment=SYNC_INTERVAL=90
Environment=MEMORY_PATH=/app/safla-memory
ExecStart=/usr/bin/python3 swarm-memory-coordinator.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Set up log rotation
cat > /etc/logrotate.d/tge-coordinator << 'EOF'
/app/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 ec2-user ec2-user
    postrotate
        systemctl reload tge-memory-coordinator || true
    endscript
}
EOF

# Create health check script
cat > /app/health-check.sh << 'EOF'
#!/bin/bash
# Health check script for Memory Coordinator

HEALTH_URL="http://localhost:8002/health"
TIMEOUT=10

# Check if service is responding
if curl -f -s --max-time $TIMEOUT $HEALTH_URL > /dev/null; then
    echo "HEALTHY: Coordinator API is responding"
    exit 0
else
    echo "UNHEALTHY: Coordinator API is not responding"
    exit 1
fi
EOF

chmod +x /app/health-check.sh

# Set up cron job for health checks
echo "*/5 * * * * ec2-user /app/health-check.sh >> /app/logs/health.log 2>&1" >> /var/spool/cron/ec2-user

# Create backup script
cat > /app/backup.sh << 'EOF'
#!/bin/bash
# Backup script for Memory Coordinator data

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
aws s3 cp $BACKUP_DIR/ s3://$S3_BUCKET/coordinator/ --recursive

# Clean up old backups (keep 7 days)
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x /app/backup.sh

# Schedule daily backups
echo "0 3 * * * ec2-user /app/backup.sh >> /app/logs/backup.log 2>&1" >> /var/spool/cron/ec2-user

# Create memory sync monitoring script
cat > /app/memory-monitor.sh << 'EOF'
#!/bin/bash
# Monitor memory synchronization status

MEMORY_DIR="/app/safla-memory"
LOG_FILE="/app/logs/memory-monitor.log"

# Check memory directory size
MEMORY_SIZE=$(du -sh $MEMORY_DIR | cut -f1)

# Check last sync time
LAST_SYNC=$(find $MEMORY_DIR -name "*.json" -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f1)
CURRENT_TIME=$(date +%s)
SYNC_AGE=$((CURRENT_TIME - LAST_SYNC))

echo "$(date): Memory size: $MEMORY_SIZE, Last sync: $SYNC_AGE seconds ago" >> $LOG_FILE

# Alert if sync is too old (more than 10 minutes)
if [ $SYNC_AGE -gt 600 ]; then
    echo "WARNING: Memory sync is older than 10 minutes" >> $LOG_FILE
fi
EOF

chmod +x /app/memory-monitor.sh

# Schedule memory monitoring
echo "*/10 * * * * ec2-user /app/memory-monitor.sh" >> /var/spool/cron/ec2-user

# Set proper ownership
chown -R ec2-user:ec2-user /app/
chown -R ec2-user:ec2-user /opt/tge-swarm/

# Enable and start services
systemctl daemon-reload
systemctl enable tge-memory-coordinator
systemctl start tge-memory-coordinator

# Install security updates
yum update -y --security

# Configure firewall
if command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=8002/tcp
    firewall-cmd --permanent --add-port=8003/tcp
    firewall-cmd --reload
fi

echo "Memory Coordinator setup completed successfully"