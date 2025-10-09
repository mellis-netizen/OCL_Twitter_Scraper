#!/bin/bash
# TGE Consul Service Discovery User Data Script
# Automated setup for Consul service discovery

set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

# Variables
ENVIRONMENT="${environment}"

# Update system
yum update -y

# Install required packages
yum install -y \
    curl \
    wget \
    unzip \
    jq \
    awscli \
    amazon-cloudwatch-agent

# Download and install Consul
CONSUL_VERSION="1.16.1"
cd /tmp
wget https://releases.hashicorp.com/consul/${CONSUL_VERSION}/consul_${CONSUL_VERSION}_linux_amd64.zip
unzip consul_${CONSUL_VERSION}_linux_amd64.zip
mv consul /usr/local/bin/
chmod +x /usr/local/bin/consul

# Create consul user
useradd --system --home /etc/consul.d --shell /bin/false consul

# Create directories
mkdir -p /opt/consul/{data,config,logs}
mkdir -p /etc/consul.d
chown -R consul:consul /opt/consul
chown -R consul:consul /etc/consul.d

# Create Consul configuration
cat > /etc/consul.d/consul.hcl << 'EOF'
datacenter = "tge-swarm-aws"
data_dir = "/opt/consul/data"
log_level = "INFO"
server = true
bootstrap_expect = 1
retry_join = []
bind_addr = "{{ GetInterfaceIP \"eth0\" }}"
client_addr = "0.0.0.0"
ui_config {
  enabled = true
}
connect {
  enabled = true
}
ports {
  grpc = 8502
}
acl = {
  enabled = false
  default_policy = "allow"
}
performance {
  raft_multiplier = 1
}
EOF

# Create systemd service
cat > /etc/systemd/system/consul.service << 'EOF'
[Unit]
Description=Consul
Documentation=https://www.consul.io/
Requires=network-online.target
After=network-online.target
ConditionFileNotEmpty=/etc/consul.d/consul.hcl

[Service]
Type=notify
User=consul
Group=consul
ExecStart=/usr/local/bin/consul agent -config-dir=/etc/consul.d/
ExecReload=/bin/kill -HUP $MAINPID
KillMode=process
Restart=on-failure
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

# Set up CloudWatch agent
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
{
    "agent": {
        "metrics_collection_interval": 60,
        "run_as_user": "cwagent"
    },
    "metrics": {
        "namespace": "TGE/Swarm/Consul",
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
                        "file_path": "/opt/consul/logs/consul.log",
                        "log_group_name": "/aws/ec2/consul",
                        "log_stream_name": "{instance_id}/consul"
                    },
                    {
                        "file_path": "/var/log/user-data.log",
                        "log_group_name": "/aws/ec2/consul",
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

# Create health check script
cat > /opt/consul/health-check.sh << 'EOF'
#!/bin/bash
# Health check script for Consul

if consul members > /dev/null 2>&1; then
    echo "HEALTHY: Consul is running and responsive"
    exit 0
else
    echo "UNHEALTHY: Consul is not responding"
    exit 1
fi
EOF

chmod +x /opt/consul/health-check.sh

# Set up cron job for health checks
echo "*/5 * * * * consul /opt/consul/health-check.sh >> /opt/consul/logs/health.log 2>&1" >> /var/spool/cron/consul

# Create backup script
cat > /opt/consul/backup.sh << 'EOF'
#!/bin/bash
# Backup script for Consul data

BACKUP_DIR="/opt/consul/backups"
S3_BUCKET="your-backup-bucket"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup Consul snapshot
consul snapshot save $BACKUP_DIR/consul-snapshot-$DATE.snap

# Upload to S3
aws s3 cp $BACKUP_DIR/ s3://$S3_BUCKET/consul/ --recursive

# Clean up old backups (keep 7 days)
find $BACKUP_DIR -name "*.snap" -mtime +7 -delete

echo "Consul backup completed: $DATE"
EOF

chmod +x /opt/consul/backup.sh

# Schedule daily backups
echo "0 5 * * * consul /opt/consul/backup.sh >> /opt/consul/logs/backup.log 2>&1" >> /var/spool/cron/consul

# Enable and start Consul
systemctl daemon-reload
systemctl enable consul
systemctl start consul

# Wait for Consul to start
sleep 10

# Register services with Consul
cat > /tmp/register-services.sh << 'EOF'
#!/bin/bash
# Register TGE Swarm services with Consul

# Wait for Consul to be ready
while ! consul members > /dev/null 2>&1; do
    echo "Waiting for Consul to be ready..."
    sleep 5
done

# Register Swarm Queen service
consul services register -name=swarm-queen -port=8080 -tag=production -tag=orchestrator

# Register Memory Coordinator service
consul services register -name=memory-coordinator -port=8002 -tag=production -tag=coordinator

echo "Services registered with Consul"
EOF

chmod +x /tmp/register-services.sh
/tmp/register-services.sh

# Install security updates
yum update -y --security

# Configure firewall
if command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=8500/tcp
    firewall-cmd --permanent --add-port=8300/tcp
    firewall-cmd --permanent --add-port=8301/tcp
    firewall-cmd --permanent --add-port=8302/tcp
    firewall-cmd --permanent --add-port=8600/udp
    firewall-cmd --reload
fi

echo "Consul setup completed successfully"