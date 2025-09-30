#!/bin/bash

# EC2 User Data Script for Crypto TGE Monitor
# This script runs automatically when a new EC2 instance starts
# Place this in the EC2 User Data field when launching an instance

set -e  # Exit on any error

# Log everything
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "Starting EC2 User Data script for Crypto TGE Monitor..."
echo "Timestamp: $(date)"
echo "Instance ID: $(curl -s http://169.254.169.254/latest/meta-data/instance-id)"

# Configuration - Update these variables
REPO_URL="https://github.com/mellis-netizen/OCL_Twitter_Scraper.git"
BRANCH="main"
DEPLOY_KEY_S3_PATH=""  # Optional: s3://bucket/path/to/deploy-key
CONFIG_S3_PATH=""      # Optional: s3://bucket/path/to/.env
S3_BACKUP_BUCKET=""    # Optional: S3 bucket for backups (leave empty to disable)

# Update system packages
echo "Updating system packages..."
apt-get update -y
apt-get upgrade -y

# Install AWS CLI if not present
if ! command -v aws &> /dev/null; then
    echo "Installing AWS CLI..."
    apt-get install -y awscli
fi

# Install git if not present
if ! command -v git &> /dev/null; then
    echo "Installing git..."
    apt-get install -y git
fi

# Create temporary directory for deployment
TEMP_DIR="/tmp/crypto-tge-deploy"
mkdir -p $TEMP_DIR
cd $TEMP_DIR

# Download deployment files
if [ -n "$REPO_URL" ] && [ "$REPO_URL" != "https://github.com/mellis-netizen/OCL_Twitter_Scraper.git" ]; then
    echo "Cloning repository: $REPO_URL"
    
    # Handle private repositories with deploy key
    if [ -n "$DEPLOY_KEY_S3_PATH" ]; then
        echo "Downloading deploy key from S3..."
        aws s3 cp "$DEPLOY_KEY_S3_PATH" /tmp/deploy-key
        chmod 600 /tmp/deploy-key
        
        # Configure git to use deploy key
        export GIT_SSH_COMMAND="ssh -i /tmp/deploy-key -o StrictHostKeyChecking=no"
    fi
    
    git clone -b "$BRANCH" "$REPO_URL" .
else
    # Fallback: download from a known location or use pre-built package
    echo "Repository URL not configured, using alternative method..."
    
    # Example: Download from S3 bucket
    # aws s3 cp s3://your-bucket/OCL_Twitter_Scraper.zip .
    # unzip OCL_Twitter_Scraper.zip
    
    echo "ERROR: No valid repository URL configured"
    exit 1
fi

# Download configuration from S3 if specified
if [ -n "$CONFIG_S3_PATH" ]; then
    echo "Downloading configuration from S3: $CONFIG_S3_PATH"
    aws s3 cp "$CONFIG_S3_PATH" .env
fi

# Make deployment script executable
chmod +x ec2-deploy.sh

# Set environment variables for deployment
if [ -n "$S3_BACKUP_BUCKET" ]; then
    export S3_BACKUP_BUCKET="$S3_BACKUP_BUCKET"
    echo "S3 backup bucket configured: $S3_BACKUP_BUCKET"
else
    echo "S3 backup bucket not configured - using local backups only"
fi

# Run the deployment
echo "Starting main deployment..."
./ec2-deploy.sh

# Configure service to auto-restart on failure
echo "Configuring service auto-restart..."
systemctl enable crypto-tge-monitor

# Create startup completion marker
echo "EC2 deployment completed at $(date)" > /var/log/crypto-tge-deploy.complete

# Send completion notification if SNS topic is configured
if [ -n "$SNS_TOPIC_ARN" ]; then
    INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
    INSTANCE_TYPE=$(curl -s http://169.254.169.254/latest/meta-data/instance-type)
    
    aws sns publish --topic-arn "$SNS_TOPIC_ARN" \
        --message "Crypto TGE Monitor successfully deployed on EC2 instance $INSTANCE_ID ($INSTANCE_TYPE)" \
        --subject "EC2 Deployment Complete" || echo "Failed to send SNS notification"
fi

echo "EC2 User Data script completed successfully!"
echo "Check service status with: systemctl status crypto-tge-monitor"