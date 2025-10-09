#!/bin/bash
# TGE Monitoring Stack User Data Script
# Automated setup for Prometheus, Grafana, and other monitoring tools

set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

# Variables
ENVIRONMENT="${environment}"

# Update system
yum update -y

# Install required packages
yum install -y \
    docker \
    docker-compose \
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

# Create monitoring directories
mkdir -p /opt/monitoring/{prometheus,grafana,alertmanager,jaeger}
mkdir -p /app/{data,config,logs}

# Mount EBS volume for monitoring data
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

# Create Prometheus configuration
mkdir -p /app/config/prometheus
cat > /app/config/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'tge-swarm-aws'
    environment: 'production'

rule_files:
  - "/etc/prometheus/rules/*.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - localhost:9093

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'swarm-queen'
    static_configs:
      - targets: ['${QUEEN_ENDPOINT}:8001']
    scrape_interval: 15s

  - job_name: 'memory-coordinator'
    static_configs:
      - targets: ['${COORDINATOR_ENDPOINT}:8003']
    scrape_interval: 30s

  - job_name: 'swarm-agents'
    ec2_sd_configs:
      - region: us-west-2
        port: 8010
        filters:
          - name: tag:Service
            values: 
              - Swarm-Agents
    relabel_configs:
      - source_labels: [__meta_ec2_tag_Name]
        target_label: instance_name
      - source_labels: [__meta_ec2_tag_AgentType]
        target_label: agent_type

  - job_name: 'node-exporter'
    ec2_sd_configs:
      - region: us-west-2
        port: 9100
        filters:
          - name: tag:Environment
            values: 
              - production
EOF

# Create Grafana provisioning
mkdir -p /app/config/grafana/{provisioning/datasources,provisioning/dashboards,dashboards}

cat > /app/config/grafana/provisioning/datasources/prometheus.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://localhost:9090
    isDefault: true
    editable: false
EOF

cat > /app/config/grafana/provisioning/dashboards/dashboard.yml << 'EOF'
apiVersion: 1

providers:
  - name: 'TGE Swarm'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
EOF

# Create AlertManager configuration
mkdir -p /app/config/alertmanager
cat > /app/config/alertmanager/config.yml << 'EOF'
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@tge-swarm.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
  - name: 'web.hook'
    webhook_configs:
      - url: 'http://localhost:5001/'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'dev', 'instance']
EOF

# Create Docker Compose for monitoring stack
cat > /opt/monitoring/docker-compose.yml << 'EOF'
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-lifecycle'
      - '--storage.tsdb.retention.size=20GB'
    ports:
      - "9090:9090"
    volumes:
      - /app/config/prometheus:/etc/prometheus
      - /app/data/prometheus:/prometheus
    restart: unless-stopped
    user: "nobody"
    
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_INSTALL_PLUGINS=redis-datasource,prometheus-plugin
    ports:
      - "3000:3000"
    volumes:
      - /app/config/grafana:/etc/grafana/provisioning
      - /app/data/grafana:/var/lib/grafana
    restart: unless-stopped
    user: "472"
    
  alertmanager:
    image: prom/alertmanager:latest
    container_name: alertmanager
    command:
      - '--config.file=/etc/alertmanager/config.yml'
      - '--storage.path=/alertmanager'
      - '--web.external-url=http://localhost:9093'
    ports:
      - "9093:9093"
    volumes:
      - /app/config/alertmanager:/etc/alertmanager
      - /app/data/alertmanager:/alertmanager
    restart: unless-stopped
    
  jaeger:
    image: jaegertracing/all-in-one:latest
    container_name: jaeger
    environment:
      - COLLECTOR_ZIPKIN_HOST_PORT=:9411
    ports:
      - "16686:16686"
      - "14268:14268"
    volumes:
      - /app/data/jaeger:/tmp
    restart: unless-stopped
    
  node-exporter:
    image: prom/node-exporter:latest
    container_name: node-exporter
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    restart: unless-stopped

networks:
  default:
    driver: bridge
EOF

# Set up CloudWatch agent
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
{
    "agent": {
        "metrics_collection_interval": 60,
        "run_as_user": "cwagent"
    },
    "metrics": {
        "namespace": "TGE/Swarm/Monitoring",
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
                        "file_path": "/var/log/user-data.log",
                        "log_group_name": "/aws/ec2/monitoring",
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

# Create backup script
cat > /app/backup.sh << 'EOF'
#!/bin/bash
# Backup script for monitoring data

BACKUP_DIR="/app/backups"
S3_BUCKET="your-backup-bucket"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup Prometheus data
tar -czf $BACKUP_DIR/prometheus_$DATE.tar.gz /app/data/prometheus/

# Backup Grafana data
tar -czf $BACKUP_DIR/grafana_$DATE.tar.gz /app/data/grafana/

# Upload to S3
aws s3 cp $BACKUP_DIR/ s3://$S3_BUCKET/monitoring/ --recursive

# Clean up old backups (keep 30 days)
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Monitoring backup completed: $DATE"
EOF

chmod +x /app/backup.sh

# Schedule daily backups
echo "0 1 * * * ec2-user /app/backup.sh >> /app/logs/backup.log 2>&1" >> /var/spool/cron/ec2-user

# Set proper ownership
chown -R ec2-user:ec2-user /app/
chown -R ec2-user:ec2-user /opt/monitoring/

# Create data directories
mkdir -p /app/data/{prometheus,grafana,alertmanager,jaeger}
chown -R 65534:65534 /app/data/prometheus
chown -R 472:472 /app/data/grafana

# Start monitoring services
cd /opt/monitoring
docker-compose up -d

# Install security updates
yum update -y --security

# Configure firewall
if command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=3000/tcp
    firewall-cmd --permanent --add-port=9090/tcp
    firewall-cmd --permanent --add-port=9093/tcp
    firewall-cmd --permanent --add-port=16686/tcp
    firewall-cmd --reload
fi

echo "Monitoring stack setup completed successfully"