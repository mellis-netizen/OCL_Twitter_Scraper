#!/bin/bash
# TGE Bastion Host User Data Script
# Automated setup for secure bastion host

set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

# Variables
ENVIRONMENT="${environment}"

# Update system
yum update -y

# Install required packages
yum install -y \
    htop \
    curl \
    wget \
    unzip \
    jq \
    awscli \
    amazon-cloudwatch-agent \
    amazon-ssm-agent \
    fail2ban

# Configure SSH hardening
sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/#MaxAuthTries 6/MaxAuthTries 3/' /etc/ssh/sshd_config
sed -i 's/#ClientAliveInterval 0/ClientAliveInterval 300/' /etc/ssh/sshd_config
sed -i 's/#ClientAliveCountMax 3/ClientAliveCountMax 2/' /etc/ssh/sshd_config

# Restart SSH service
systemctl restart sshd

# Configure fail2ban
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
backend = systemd

[sshd]
enabled = true
port = ssh
logpath = %(sshd_log)s
backend = %(sshd_backend)s
EOF

# Start and enable fail2ban
systemctl enable fail2ban
systemctl start fail2ban

# Set up CloudWatch agent
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
{
    "agent": {
        "metrics_collection_interval": 60,
        "run_as_user": "cwagent"
    },
    "metrics": {
        "namespace": "TGE/Swarm/Bastion",
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
                        "file_path": "/var/log/secure",
                        "log_group_name": "/aws/ec2/bastion",
                        "log_stream_name": "{instance_id}/secure"
                    },
                    {
                        "file_path": "/var/log/user-data.log",
                        "log_group_name": "/aws/ec2/bastion",
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

# Enable and start SSM agent
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent

# Create connection monitoring script
cat > /home/ec2-user/monitor-connections.sh << 'EOF'
#!/bin/bash
# Monitor SSH connections

LOG_FILE="/var/log/ssh-connections.log"

# Log current connections
WHO_OUTPUT=$(who)
SS_OUTPUT=$(ss -tnp | grep :22)

if [ ! -z "$WHO_OUTPUT" ]; then
    echo "$(date): Active SSH sessions:" >> $LOG_FILE
    echo "$WHO_OUTPUT" >> $LOG_FILE
fi

if [ ! -z "$SS_OUTPUT" ]; then
    echo "$(date): SSH connections:" >> $LOG_FILE
    echo "$SS_OUTPUT" >> $LOG_FILE
fi
EOF

chmod +x /home/ec2-user/monitor-connections.sh

# Schedule connection monitoring
echo "*/10 * * * * /home/ec2-user/monitor-connections.sh" >> /var/spool/cron/ec2-user

# Create tunnel helper script
cat > /home/ec2-user/create-tunnel.sh << 'EOF'
#!/bin/bash
# Helper script for creating SSH tunnels to private instances

show_usage() {
    echo "Usage: $0 <target-ip> <local-port> <remote-port>"
    echo "Example: $0 10.0.1.100 8080 8080"
}

if [ $# -ne 3 ]; then
    show_usage
    exit 1
fi

TARGET_IP=$1
LOCAL_PORT=$2
REMOTE_PORT=$3

echo "Creating SSH tunnel: localhost:$LOCAL_PORT -> $TARGET_IP:$REMOTE_PORT"
ssh -L $LOCAL_PORT:$TARGET_IP:$REMOTE_PORT -N ec2-user@$TARGET_IP
EOF

chmod +x /home/ec2-user/create-tunnel.sh

# Create security audit script
cat > /home/ec2-user/security-audit.sh << 'EOF'
#!/bin/bash
# Security audit script for bastion host

AUDIT_LOG="/var/log/security-audit.log"

echo "=== Security Audit - $(date) ===" >> $AUDIT_LOG

# Check for failed login attempts
echo "Failed SSH attempts in last 24 hours:" >> $AUDIT_LOG
journalctl --since "24 hours ago" | grep "Failed password" | wc -l >> $AUDIT_LOG

# Check active users
echo "Currently logged in users:" >> $AUDIT_LOG
who >> $AUDIT_LOG

# Check fail2ban status
echo "Fail2ban status:" >> $AUDIT_LOG
fail2ban-client status sshd >> $AUDIT_LOG 2>&1

# Check system updates
echo "Available security updates:" >> $AUDIT_LOG
yum check-update --security | wc -l >> $AUDIT_LOG

echo "=== End Audit ===" >> $AUDIT_LOG
EOF

chmod +x /home/ec2-user/security-audit.sh

# Schedule daily security audit
echo "0 6 * * * /home/ec2-user/security-audit.sh" >> /var/spool/cron/ec2-user

# Set proper ownership
chown ec2-user:ec2-user /home/ec2-user/*.sh

# Install additional security tools
yum install -y \
    nmap \
    tcpdump \
    netstat-nat \
    lsof

# Create MOTD with security notice
cat > /etc/motd << 'EOF'
================================================================================
                     TGE Swarm Bastion Host - PRODUCTION
================================================================================

WARNING: This is a production bastion host for the TGE Swarm infrastructure.
All activities are logged and monitored.

Authorized users only. Disconnect immediately if you are not authorized.

Connection guidelines:
- Use this host only for accessing private TGE Swarm infrastructure
- Do not install unauthorized software
- Report any suspicious activity immediately
- Follow the principle of least privilege

For assistance, contact the TGE Swarm operations team.

================================================================================
EOF

# Configure automatic security updates
yum install -y yum-cron
sed -i 's/apply_updates = no/apply_updates = yes/' /etc/yum/yum-cron.conf
sed -i 's/update_level = default/update_level = security/' /etc/yum/yum-cron.conf
systemctl enable yum-cron
systemctl start yum-cron

# Configure firewall (if available)
if command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-service=ssh
    firewall-cmd --reload
fi

echo "Bastion host setup completed successfully"