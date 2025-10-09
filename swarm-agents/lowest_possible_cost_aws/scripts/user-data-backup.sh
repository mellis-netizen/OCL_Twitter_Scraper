#!/bin/bash
# User Data Script for Ultra-Low-Cost TGE Swarm Backup Instance
# Cost Optimization Engineer: Claude

set -e

# Variables from Terraform
REGION="${region}"

# Log everything
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "Starting TGE Swarm Backup Instance Setup..."

# Update system (minimal updates only)
yum update -y --security

# Install minimal required packages
yum install -y \
    aws-cli \
    curl \
    wget \
    rsync \
    cronie

# Create backup user
useradd -m -s /bin/bash backup-user

# Create backup directory
mkdir -p /opt/backup
chown backup-user:backup-user /opt/backup

# Set up backup monitoring script
cat > /opt/backup/monitor-main-instance.sh << 'EOF'
#!/bin/bash
# Monitor main instance and prepare for failover if needed

MAIN_INSTANCE_IP=$(aws ec2 describe-instances \
    --region $REGION \
    --filters "Name=tag:Name,Values=*main*" "Name=instance-state-name,Values=running" \
    --query 'Reservations[0].Instances[0].PrivateIpAddress' \
    --output text)

if [ "$MAIN_INSTANCE_IP" != "None" ] && [ -n "$MAIN_INSTANCE_IP" ]; then
    # Test connection to main instance
    if curl -f --connect-timeout 10 "http://$MAIN_INSTANCE_IP:8080/health" >/dev/null 2>&1; then
        echo "$(date): Main instance healthy at $MAIN_INSTANCE_IP"
        
        # Sync latest backups from main instance
        rsync -av ec2-user@$MAIN_INSTANCE_IP:/opt/tge-swarm/backups/ /opt/backup/synced/ 2>/dev/null || true
        
    else
        echo "$(date): Main instance unhealthy or unreachable"
        
        # Send alert
        aws sns publish --region $REGION \
            --topic-arn $(aws ssm get-parameter --name "/tge-swarm/sns-topic-arn" --query "Parameter.Value" --output text 2>/dev/null || echo "arn:aws:sns:$REGION:123456789012:tge-swarm-alerts") \
            --message "Main TGE Swarm instance appears to be down. Backup instance standing by." \
            --subject "TGE Swarm Main Instance Health Alert"
    fi
else
    echo "$(date): No running main instance found"
fi
EOF

chmod +x /opt/backup/monitor-main-instance.sh

# Set up emergency restore script
cat > /opt/backup/emergency-restore.sh << 'EOF'
#!/bin/bash
# Emergency restore script for backup instance activation

echo "$(date): Emergency restore initiated"

# Install Docker and Docker Compose
yum install -y docker
systemctl start docker
systemctl enable docker

curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create application directory
mkdir -p /opt/tge-swarm-restore
cd /opt/tge-swarm-restore

# Copy backup files
cp -r /opt/backup/synced/* . 2>/dev/null || echo "No synced backups found"

# Download latest backup from S3 if available
if [ -n "$BACKUP_S3_BUCKET" ]; then
    aws s3 sync "s3://$BACKUP_S3_BUCKET/emergency-backups/" ./s3-backups/
    
    # Extract latest backup
    LATEST_BACKUP=$(ls -t ./s3-backups/*.tar.gz | head -1)
    if [ -n "$LATEST_BACKUP" ]; then
        tar -xzf "$LATEST_BACKUP" -C .
    fi
fi

# Start minimal services for emergency operation
cat > docker-compose-emergency.yml << 'COMPOSE_EOF'
version: '3.8'
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: tge_swarm
      POSTGRES_USER: swarm_user
      POSTGRES_PASSWORD: swarm_secure_pass
    volumes:
      - ./database.sql:/docker-entrypoint-initdb.d/restore.sql
    ports:
      - "5432:5432"
    
  nginx:
    image: nginx:alpine
    volumes:
      - ./emergency-nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
COMPOSE_EOF

# Create emergency nginx config
cat > emergency-nginx.conf << 'NGINX_EOF'
events { worker_connections 1024; }
http {
    server {
        listen 80;
        location / {
            return 503 "TGE Swarm is temporarily unavailable. Emergency restore in progress.";
            add_header Content-Type text/plain;
        }
        location /health {
            return 200 "Emergency instance active";
            add_header Content-Type text/plain;
        }
    }
}
NGINX_EOF

# Start emergency services
docker-compose -f docker-compose-emergency.yml up -d

echo "$(date): Emergency restore completed. Basic services running."
EOF

chmod +x /opt/backup/emergency-restore.sh

# Set up cron job for monitoring
echo "*/5 * * * * backup-user /opt/backup/monitor-main-instance.sh >> /var/log/backup-monitor.log 2>&1" >> /etc/crontab

# Set up log rotation for backup logs
cat > /etc/logrotate.d/backup-monitor << 'EOF'
/var/log/backup-monitor.log {
    daily
    rotate 3
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    maxsize 10M
}
EOF

# Create SSH key for backup user to access main instance
sudo -u backup-user ssh-keygen -t rsa -b 2048 -f /home/backup-user/.ssh/id_rsa -N ""

# Set up basic system monitoring
cat > /opt/backup/system-stats.sh << 'EOF'
#!/bin/bash
# Basic system statistics

echo "$(date): System Stats"
echo "Memory Usage: $(free -m | awk 'NR==2{printf "%.1f%%", $3*100/$2 }')"
echo "Disk Usage: $(df -h / | awk 'NR==2{print $5}')"
echo "Load Average: $(uptime | awk -F'load average:' '{ print $2 }')"
echo "---"
EOF

chmod +x /opt/backup/system-stats.sh

# Add system stats to cron
echo "0 * * * * backup-user /opt/backup/system-stats.sh >> /var/log/system-stats.log" >> /etc/crontab

# Start cron service
systemctl start crond
systemctl enable crond

# Create completion marker
touch /opt/backup/setup-complete

echo "TGE Swarm Backup Instance Setup Complete!"
echo "Monitoring main instance every 5 minutes"
echo "Emergency restore available at: /opt/backup/emergency-restore.sh"