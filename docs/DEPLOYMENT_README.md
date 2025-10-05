# 🚀 Enhanced TGE Monitor System - Complete Deployment Guide

This directory contains everything you need to deploy the Enhanced TGE Monitor System on AWS EC2. Choose your deployment method based on your preference and experience level.

## 📋 Deployment Options

### Option 1: One-Command Deployment (Recommended)
**Best for:** Quick setup, automated deployment
```bash
./deploy-complete.sh your-aws-key-name us-east-1
```

### Option 2: Step-by-Step Deployment
**Best for:** Learning, troubleshooting, custom configurations

#### Step A: Launch EC2 Instance
```bash
./launch-ec2-instance.sh your-aws-key-name us-east-1
```

#### Step B: Deploy Application
```bash
# SSH to your instance
ssh -i ~/.ssh/your-aws-key-name.pem ubuntu@your-instance-ip

# Upload deployment script
scp -i ~/.ssh/your-aws-key-name.pem deploy-ec2-automated.sh ubuntu@your-instance-ip:~/

# Run deployment
./deploy-ec2-automated.sh
```

### Option 3: Manual Deployment
**Best for:** Advanced users, custom environments
Follow the detailed guide: [EC2_DEPLOYMENT_GUIDE_COMPLETE.md](EC2_DEPLOYMENT_GUIDE_COMPLETE.md)

## 📁 Deployment Files

| File | Purpose | When to Use |
|------|---------|-------------|
| `deploy-complete.sh` | One-command full deployment | Quick automated setup |
| `launch-ec2-instance.sh` | EC2 instance creation only | Step-by-step deployment |
| `deploy-ec2-automated.sh` | Application deployment only | Run on existing EC2 instance |
| `verify-deployment.sh` | System verification | After deployment completion |
| `EC2_DEPLOYMENT_GUIDE_COMPLETE.md` | Detailed manual guide | Learning/troubleshooting |

## 🔧 Prerequisites

### Local Machine Requirements
- AWS CLI installed and configured
- SSH key pair created in your AWS region
- Internet connection
- Git (for cloning repository)

### AWS Requirements
- AWS account with EC2 access
- IAM permissions for EC2, VPC, Security Groups
- Available Elastic IP (optional)
- Domain name (optional, for SSL)

## 🚀 Quick Start (5 Minutes)

1. **Setup AWS CLI** (if not done):
   ```bash
   aws configure
   # Enter your AWS Access Key ID, Secret, Region, and Output format
   ```

2. **Create SSH Key** (if not done):
   ```bash
   aws ec2 create-key-pair --key-name tge-monitor-key --query 'KeyMaterial' --output text > ~/.ssh/tge-monitor-key.pem
   chmod 400 ~/.ssh/tge-monitor-key.pem
   ```
   
   📖 **Need help with AWS keys?** See detailed guide: [SETUP_AWS_KEYS.md](SETUP_AWS_KEYS.md)

3. **Deploy Everything**:
   ```bash
   ./deploy-complete.sh tge-monitor-key us-east-1
   ```

4. **Wait** (~10-15 minutes) for deployment to complete

5. **Access Your System**:
   - API Docs: `http://your-instance-ip/docs`
   - Health Check: `http://your-instance-ip/health`

## 🔍 Deployment Verification

After deployment, verify everything is working:

```bash
# Option 1: Run verification script remotely
./verify-deployment.sh your-instance-ip

# Option 2: Run on the server itself
ssh -i ~/.ssh/your-key.pem ubuntu@your-instance-ip
./verify-deployment.sh
```

## 📊 What Gets Deployed

### System Components
- **Ubuntu 22.04 LTS** on t3.large EC2 instance
- **Python 3.11** with virtual environment
- **PostgreSQL 15** database server
- **Redis 7** cache server
- **Nginx** reverse proxy
- **SSL/TLS** support (Let's Encrypt ready)

### Application Components
- **TGE Monitor API** (FastAPI)
- **Background Worker** (monitoring service)
- **WebSocket Server** (real-time alerts)
- **Rate Limiting** (advanced strategies)
- **Authentication** (JWT + API keys)
- **Database Integration** (PostgreSQL)
- **Caching** (Redis)

### Security & Monitoring
- **Firewall Configuration** (UFW)
- **Fail2ban** intrusion prevention
- **Health Monitoring** (automated checks)
- **Log Rotation** (automated cleanup)
- **Backup Scripts** (daily automated backups)
- **Service Management** (systemd)

## 🔧 Post-Deployment Configuration

### 1. Configure Email Settings
```bash
ssh -i ~/.ssh/your-key.pem ubuntu@your-instance-ip
sudo vim /opt/tge-monitor/.env
```

Update email configuration:
```env
SMTP_SERVER=smtp.maileroo.com
SMTP_PORT=587
EMAIL_USER=your_email@domain.com
EMAIL_PASSWORD=your_email_password
RECIPIENT_EMAIL=alerts@yourdomain.com
```

### 2. Add Twitter API Credentials (Optional)
```env
TWITTER_BEARER_TOKEN=your_twitter_bearer_token
```

### 3. Setup SSL Certificate (Recommended)
```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate (replace with your domain)
sudo certbot --nginx -d yourdomain.com

# Auto-renewal is automatically configured
```

### 4. Configure Domain Name (Optional)
Update your DNS records to point to your EC2 instance IP address.

## 📈 Monitoring & Maintenance

### Check System Status
```bash
# Service status
sudo systemctl status tge-monitor-api
sudo systemctl status tge-monitor-worker

# Application logs
tail -f /opt/tge-monitor/logs/*.log

# System health
/opt/tge-monitor/health_check.sh
```

### Performance Monitoring
- **Logs**: `/opt/tge-monitor/logs/`
- **Metrics**: Available via API at `/health`
- **Backups**: `/opt/tge-monitor/backups/`
- **Reports**: `/opt/tge-monitor/reports/`

### Automated Tasks
- **Health checks**: Every 5 minutes
- **Backups**: Daily at 2 AM
- **Log rotation**: Daily (14-day retention)
- **Security updates**: Weekly

## 🐛 Troubleshooting

### Common Issues

#### 1. Deployment Script Fails
```bash
# Check deployment log
tail -f /tmp/tge-monitor-deployment.log

# Check specific service
sudo journalctl -u tge-monitor-api -f
```

#### 2. API Not Responding
```bash
# Check if port is listening
sudo netstat -tlnp | grep 8000

# Restart API service
sudo systemctl restart tge-monitor-api

# Check Nginx configuration
sudo nginx -t
```

#### 3. Database Connection Issues
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test database connection
sudo -u postgres psql -c "SELECT 1"

# Check database logs
sudo tail -f /var/log/postgresql/*.log
```

#### 4. High Resource Usage
```bash
# Check memory usage
free -h

# Check CPU usage
htop

# Restart services if needed
sudo systemctl restart tge-monitor-*
```

### Getting Help

1. **Check Logs**: Always start with checking the logs
2. **Verify Configuration**: Ensure `.env` file is correctly configured
3. **Test Components**: Use the verification script
4. **Restart Services**: Try restarting individual services
5. **Check GitHub Issues**: Look for similar problems in the repository

## 🔒 Security Best Practices

### Immediate Actions
1. **Change Default Passwords**: Check `/opt/tge-monitor/DEPLOYMENT_CREDENTIALS.txt`
2. **Configure Email**: Set up proper email credentials
3. **Setup SSL**: Use Let's Encrypt for HTTPS
4. **Review Firewall**: Ensure only necessary ports are open

### Ongoing Security
1. **Regular Updates**: System automatically updates security patches
2. **Monitor Logs**: Check for suspicious activity
3. **Backup Verification**: Ensure backups are working
4. **Access Review**: Regularly review who has access

## 💰 Cost Optimization

### EC2 Instance Costs
- **t3.large**: ~$70/month (recommended for production)
- **t3.medium**: ~$35/month (suitable for light usage)
- **t3.small**: ~$17/month (testing only)

### Cost Reduction Tips
1. **Use Reserved Instances**: Up to 75% savings for long-term usage
2. **Monitor Usage**: Use CloudWatch to track resource utilization
3. **Scale Down**: Switch to smaller instance if usage is low
4. **Scheduled Shutdown**: Stop instance during non-business hours if appropriate

## 📞 Support

For issues with:
- **Deployment Scripts**: Check this repository's issues
- **AWS Services**: Contact AWS Support
- **Application Features**: Review the main documentation
- **Custom Configurations**: Follow the manual deployment guide

## 🎉 Success Metrics

Your deployment is successful when:
- ✅ All services are running (`systemctl status tge-monitor-*`)
- ✅ API responds at `/health` endpoint
- ✅ WebSocket connections work
- ✅ Database is accessible
- ✅ Email notifications can be sent
- ✅ Monitoring and backups are functional

---

**Congratulations! Your Enhanced TGE Monitor System is now deployed and ready for production use!** 🚀