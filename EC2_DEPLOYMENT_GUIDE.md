# EC2 Deployment Guide

Complete step-by-step guide to deploy the Crypto TGE Monitor on AWS EC2.

## Prerequisites

Before you begin, ensure you have:

- AWS account with appropriate permissions
- EC2 key pair created in your target region
- Email account credentials (Gmail recommended)
- Optional: Twitter API credentials
- Optional: S3 bucket for backups

## Deployment Methods

Choose one of these deployment methods based on your needs:

### Method 1: One-Command Deployment (Recommended)
### Method 2: CloudFormation Template (Infrastructure as Code)
### Method 3: Manual EC2 Setup
### Method 4: Docker Deployment

---

## Method 1: One-Command Deployment (Fastest)

### Step 1: Launch EC2 Instance

1. **Go to AWS EC2 Console**
   - Navigate to https://console.aws.amazon.com/ec2/
   - Select your preferred region (e.g., us-east-1)

2. **Launch Instance**
   ```
   • Click "Launch Instance"
   • Name: crypto-tge-monitor
   • AMI: Ubuntu Server 22.04 LTS
   • Instance Type: t3.small (minimum recommended)
   • Key Pair: Select your existing key pair
   • Security Group: Create new or use existing
     - Allow SSH (22) from your IP
     - Allow HTTP (80) for health checks
     - Allow HTTPS (443) for health checks
   ```

3. **Configure Security Group**
   ```
   Inbound Rules:
   • SSH (22): Your IP address
   • HTTP (80): 0.0.0.0/0 (for health checks)
   • HTTPS (443): 0.0.0.0/0 (for health checks)
   
   Outbound Rules:
   • All traffic: 0.0.0.0/0 (for internet access)
   ```

### Step 2: Connect to Instance

```bash
# Replace with your key file and instance IP
ssh -i your-key.pem ubuntu@your-ec2-ip
```

### Step 3: Run Deployment Script

```bash
# Download and run the deployment script
curl -sSL https://raw.githubusercontent.com/mellis-netizen/OCL_Twitter_Scraper/main/ec2-deploy.sh | sudo bash
```

### Step 4: Configure Credentials

```bash
# Edit the environment configuration
sudo nano /opt/crypto-tge-monitor/.env
```

**Required Configuration:**
```bash
# Email Settings (Required)
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
RECIPIENT_EMAIL=recipient@example.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Twitter API (Optional)
TWITTER_BEARER_TOKEN=your-bearer-token

# S3 Backup (Optional)
S3_BACKUP_BUCKET=your-backup-bucket
```

### Step 5: Start the Service

```bash
# Restart the service with new configuration
sudo systemctl restart crypto-tge-monitor

# Check service status
sudo systemctl status crypto-tge-monitor

# View logs
sudo journalctl -u crypto-tge-monitor -f
```

### Step 6: Verify Deployment

```bash
# Test health endpoint
curl http://localhost/health

# Check service status
curl http://localhost/status
```

---

## Method 2: CloudFormation Template (Infrastructure as Code)

### Step 1: Download Template

```bash
# Download the CloudFormation template
wget https://raw.githubusercontent.com/mellis-netizen/OCL_Twitter_Scraper/main/cloudformation-template.yaml
```

### Step 2: Deploy Stack

```bash
# Deploy using AWS CLI
aws cloudformation create-stack \
  --stack-name crypto-tge-monitor \
  --template-body file://cloudformation-template.yaml \
  --parameters \
    ParameterKey=InstanceType,ParameterValue=t3.small \
    ParameterKey=KeyPairName,ParameterValue=your-key-pair \
    ParameterKey=EmailAddress,ParameterValue=your-email@example.com \
    ParameterKey=EnableS3Backup,ParameterValue=true \
  --capabilities CAPABILITY_IAM
```

### Step 3: Wait for Completion

```bash
# Monitor stack creation
aws cloudformation describe-stacks \
  --stack-name crypto-tge-monitor \
  --query 'Stacks[0].StackStatus'
```

### Step 4: Get Instance Information

```bash
# Get instance IP
aws cloudformation describe-stacks \
  --stack-name crypto-tge-monitor \
  --query 'Stacks[0].Outputs'
```

### Step 5: Configure and Verify

Follow Steps 4-6 from Method 1 above.

---

## Method 3: Manual EC2 Setup

### Step 1: Launch EC2 Instance

Follow Step 1 from Method 1, but don't add any user data.

### Step 2: Connect and Prepare

```bash
# Connect to instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install git
sudo apt install -y git
```

### Step 3: Clone Repository

```bash
# Clone the repository
git clone https://github.com/mellis-netizen/OCL_Twitter_Scraper.git
cd OCL_Twitter_Scraper
```

### Step 4: Run Deployment Script

```bash
# Make script executable and run
chmod +x ec2-deploy.sh
sudo ./ec2-deploy.sh
```

### Step 5: Configure and Start

Follow Steps 4-6 from Method 1 above.

---

## Method 4: Docker Deployment

### Step 1: Launch EC2 Instance

Launch an EC2 instance as described in Method 1.

### Step 2: Install Docker

```bash
# Connect to instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo apt install -y docker-compose

# Logout and login again for group changes
exit
ssh -i your-key.pem ubuntu@your-ec2-ip
```

### Step 3: Clone and Deploy

```bash
# Clone repository
git clone https://github.com/mellis-netizen/OCL_Twitter_Scraper.git
cd OCL_Twitter_Scraper

# Create environment file
cp .env.example .env
nano .env  # Edit with your credentials

# Deploy with Docker
cd docker
./docker-deploy.sh deploy
```

### Step 4: Verify Docker Deployment

```bash
# Check services
docker-compose ps

# View logs
docker-compose logs -f crypto-tge-monitor

# Test endpoints
curl http://localhost/health
curl http://localhost:3000  # Grafana dashboard
```

---

## Post-Deployment Configuration

### Email Setup (Gmail)

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate App Password**:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate password for "Mail"
3. **Use App Password** in EMAIL_PASSWORD field

### Twitter API Setup (Optional)

1. **Apply for Twitter Developer Account**
2. **Create App** and get Bearer Token
3. **Add Token** to TWITTER_BEARER_TOKEN field

### S3 Backup Setup (Optional)

1. **Create S3 Bucket**:
   ```bash
   aws s3 mb s3://your-backup-bucket-name
   ```

2. **Set Bucket Policy** (if needed)
3. **Add Bucket Name** to S3_BACKUP_BUCKET field

### Health Monitoring

The system provides several health check endpoints:

```bash
# Basic health check
curl http://your-ec2-ip/health

# Detailed status
curl http://your-ec2-ip/status

# Prometheus metrics
curl http://your-ec2-ip/metrics

# Readiness check
curl http://your-ec2-ip/ready
```

---

## Troubleshooting

### Common Issues

1. **Service Won't Start**
   ```bash
   # Check logs
   sudo journalctl -u crypto-tge-monitor -n 50
   
   # Check configuration
   sudo nano /opt/crypto-tge-monitor/.env
   
   # Restart service
   sudo systemctl restart crypto-tge-monitor
   ```

2. **Email Not Sending**
   ```bash
   # Test email configuration
   cd /opt/crypto-tge-monitor
   sudo -u crypto-tge-monitor python3 -c "
   from src.email_notifier import EmailNotifier
   notifier = EmailNotifier()
   print('Email config valid:', notifier.validate_connection())
   "
   ```

3. **High Memory Usage**
   ```bash
   # Check memory usage
   free -h
   htop
   
   # Restart service if needed
   sudo systemctl restart crypto-tge-monitor
   ```

4. **Health Checks Failing**
   ```bash
   # Check NGINX status
   sudo systemctl status nginx
   
   # Check application status
   sudo systemctl status crypto-tge-monitor
   
   # Test direct connection
   curl http://localhost:8080/health
   ```

### Log Locations

```bash
# Application logs
sudo tail -f /var/log/crypto-tge-monitor/crypto_monitor.log

# System logs
sudo journalctl -u crypto-tge-monitor -f

# NGINX logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Useful Commands

```bash
# Check service status
sudo systemctl status crypto-tge-monitor

# Restart service
sudo systemctl restart crypto-tge-monitor

# View recent logs
sudo journalctl -u crypto-tge-monitor -n 100

# Check disk space
df -h

# Check memory usage
free -h

# Test email notification
sudo systemctl reload crypto-tge-monitor
```

---

## Maintenance

### Updates

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update application (if using git)
cd /opt/crypto-tge-monitor/current
sudo git pull origin main
sudo systemctl restart crypto-tge-monitor
```

### Backups

```bash
# Manual backup
sudo /opt/crypto-tge-monitor/scripts/backup.sh

# List backups
ls -la /opt/crypto-tge-monitor/backups/

# S3 backups (if configured)
aws s3 ls s3://your-backup-bucket/crypto-tge-monitor/
```

### Monitoring

- **CloudWatch**: Logs and metrics automatically sent (if using CloudFormation)
- **Health Endpoints**: Built-in health monitoring
- **Email Alerts**: System sends alerts for failures
- **Log Rotation**: Automatic log management configured

---

## Security Considerations

1. **Restrict SSH Access**: Only allow SSH from your IP
2. **Use IAM Roles**: For S3 and CloudWatch access (CloudFormation handles this)
3. **Secure Credentials**: Never commit credentials to version control
4. **Regular Updates**: Keep system and packages updated
5. **Monitor Logs**: Regularly check logs for unusual activity
6. **Backup Encryption**: S3 backups are encrypted by default

---

## Cost Optimization

### Instance Recommendations

- **t3.micro**: $7/month (testing only)
- **t3.small**: $15/month (recommended for production)
- **t3.medium**: $30/month (heavy workloads)

### Cost-Saving Tips

1. **Use Spot Instances** for non-critical workloads
2. **Schedule Shutdown** during non-business hours (optional)
3. **Monitor CloudWatch** usage to avoid unexpected charges
4. **S3 Lifecycle Policies** for backup cost optimization

---

## Support

For issues or questions:

1. **Check Logs**: Application and system logs first
2. **Health Endpoints**: Use built-in health checks
3. **GitHub Issues**: Report bugs or feature requests
4. **Documentation**: Refer to README.md and CLAUDE.md

---

## Next Steps

After successful deployment:

1. **Monitor Email Alerts**: Ensure you receive test notifications
2. **Configure Schedules**: System runs weekly by default (Monday 8 AM PST)
3. **Set Up Monitoring**: Use CloudWatch dashboards
4. **Review Logs**: Check for any initial issues
5. **Test Recovery**: Verify automatic restart capabilities

Your Crypto TGE Monitor is now production-ready! 🚀