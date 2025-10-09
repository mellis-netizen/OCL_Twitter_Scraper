#!/bin/bash
# TGE Swarm Agents User Data Script
# Automated setup and configuration for Swarm Agents

set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

# Variables
ENVIRONMENT="${environment}"
POSTGRES_ENDPOINT="${postgres_endpoint}"
REDIS_ENDPOINT="${redis_endpoint}"
QUEEN_ENDPOINT="${queen_endpoint}"
COORDINATOR_ENDPOINT="${coordinator_endpoint}"

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
mkdir -p /app/{config,logs,reports}

# Set up CloudWatch agent
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
{
    "agent": {
        "metrics_collection_interval": 60,
        "run_as_user": "cwagent"
    },
    "metrics": {
        "namespace": "TGE/Swarm/Agents",
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
                        "file_path": "/app/logs/agent.log",
                        "log_group_name": "/aws/ec2/swarm-agents",
                        "log_stream_name": "{instance_id}/agent"
                    },
                    {
                        "file_path": "/var/log/user-data.log",
                        "log_group_name": "/aws/ec2/swarm-agents",
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

# Determine agent type based on instance tags
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
AGENT_TYPE=$(aws ec2 describe-tags --filters "Name=resource-id,Values=$INSTANCE_ID" "Name=key,Values=AgentType" --query 'Tags[0].Value' --output text --region us-west-2)

if [ "$AGENT_TYPE" = "None" ]; then
    # Default to a random agent type if not specified
    AGENT_TYPES=("scraping-efficiency-specialist" "tge-keyword-precision-specialist" "api-reliability-optimizer" "performance-bottleneck-eliminator" "data-quality-enforcer")
    AGENT_TYPE=${AGENT_TYPES[$RANDOM % ${#AGENT_TYPES[@]}]}
fi

# Create configuration files
cat > /app/config/agent-config.yaml << EOF
environment: ${ENVIRONMENT}
agent:
  type: $AGENT_TYPE
  id: ${INSTANCE_ID}
  
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
    endpoint: ${COORDINATOR_ENDPOINT}
    port: 8002

agent_config:
  metrics_port: 8010
  log_level: INFO
  max_memory: 512M
  update_interval: 30

monitoring:
  prometheus_enabled: true
  
logging:
  level: INFO
  format: json
  output: /app/logs/agent.log
EOF

# Create systemd service for Swarm Agent
cat > /etc/systemd/system/tge-swarm-agent.service << EOF
[Unit]
Description=TGE Swarm Agent ($AGENT_TYPE)
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/tge-swarm/swarm-agents
Environment=PYTHONPATH=/opt/tge-swarm/swarm-agents
Environment=CONFIG_PATH=/app/config/agent-config.yaml
Environment=AGENT_TYPE=$AGENT_TYPE
Environment=AGENT_ID=${INSTANCE_ID}
Environment=LOG_LEVEL=INFO
ExecStart=/usr/bin/python3 agents/${AGENT_TYPE}.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Set up log rotation
cat > /etc/logrotate.d/tge-agent << 'EOF'
/app/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 ec2-user ec2-user
    postrotate
        systemctl reload tge-swarm-agent || true
    endscript
}
EOF

# Create health check script
cat > /app/health-check.sh << 'EOF'
#!/bin/bash
# Health check script for Swarm Agent

HEALTH_URL="http://localhost:8010/health"
TIMEOUT=10

# Check if service is responding
if curl -f -s --max-time $TIMEOUT $HEALTH_URL > /dev/null; then
    echo "HEALTHY: Agent is responding"
    exit 0
else
    echo "UNHEALTHY: Agent is not responding"
    exit 1
fi
EOF

chmod +x /app/health-check.sh

# Set up cron job for health checks
echo "*/5 * * * * ec2-user /app/health-check.sh >> /app/logs/health.log 2>&1" >> /var/spool/cron/ec2-user

# Create backup script
cat > /app/backup.sh << 'EOF'
#!/bin/bash
# Backup script for Swarm Agent data

BACKUP_DIR="/app/backups"
S3_BUCKET="your-backup-bucket"
DATE=$(date +%Y%m%d_%H%M%S)
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup configuration
tar -czf $BACKUP_DIR/config_$DATE.tar.gz /app/config/

# Backup logs
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz /app/logs/

# Upload to S3
aws s3 cp $BACKUP_DIR/ s3://$S3_BUCKET/agents/$INSTANCE_ID/ --recursive

# Clean up old backups (keep 7 days)
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x /app/backup.sh

# Schedule daily backups
echo "0 4 * * * ec2-user /app/backup.sh >> /app/logs/backup.log 2>&1" >> /var/spool/cron/ec2-user

# Create performance monitoring script
cat > /app/performance-monitor.sh << 'EOF'
#!/bin/bash
# Monitor agent performance metrics

LOG_FILE="/app/logs/performance.log"

# Get CPU and memory usage
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')
MEM_USAGE=$(free | grep Mem | awk '{printf("%.2f", $3/$2 * 100.0)}')

# Get service response time
RESPONSE_TIME=$(curl -w "%{time_total}" -s -o /dev/null http://localhost:8010/health)

echo "$(date): CPU: ${CPU_USAGE}%, Memory: ${MEM_USAGE}%, Response: ${RESPONSE_TIME}s" >> $LOG_FILE

# Send metrics to CloudWatch
aws cloudwatch put-metric-data \
    --namespace "TGE/Swarm/Agent" \
    --metric-data MetricName=ResponseTime,Value=$RESPONSE_TIME,Unit=Seconds \
    --region us-west-2
EOF

chmod +x /app/performance-monitor.sh

# Schedule performance monitoring
echo "*/15 * * * * ec2-user /app/performance-monitor.sh" >> /var/spool/cron/ec2-user

# Set proper ownership
chown -R ec2-user:ec2-user /app/
chown -R ec2-user:ec2-user /opt/tge-swarm/

# Enable and start services
systemctl daemon-reload
systemctl enable tge-swarm-agent
systemctl start tge-swarm-agent

# Install security updates
yum update -y --security

# Configure firewall
if command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=8010/tcp
    firewall-cmd --reload
fi

echo "Swarm Agent ($AGENT_TYPE) setup completed successfully"