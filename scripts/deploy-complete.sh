#!/bin/bash

# ===============================================================================
# Enhanced TGE Monitor System - One-Command Complete Deployment
# ===============================================================================
# 
# This script handles both EC2 instance creation and application deployment
# Run from your local machine with proper AWS credentials
#
# Usage: ./deploy-complete.sh <key-name> [region]
# Example: ./deploy-complete.sh my-aws-key us-east-1
# ===============================================================================

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

main() {
    local key_name="$1"
    local region="${2:-us-east-1}"
    
    if [ -z "$key_name" ]; then
        print_error "Usage: $0 <key-name> [region]"
        print_error "Example: $0 my-aws-key us-east-1"
        exit 1
    fi
    
    echo "==============================================================================="
    echo "          Enhanced TGE Monitor - Complete Deployment"
    echo "==============================================================================="
    echo ""
    print_status "This will:"
    echo "  1. Launch a new EC2 instance"
    echo "  2. Deploy the complete TGE Monitor system"
    echo "  3. Configure all services and security"
    echo ""
    
    # Step 1: Launch EC2 instance
    print_status "Step 1: Launching EC2 instance..."
    if [ -f "launch-ec2-instance.sh" ]; then
        chmod +x launch-ec2-instance.sh
        ./launch-ec2-instance.sh "$key_name" "$region"
    else
        print_error "launch-ec2-instance.sh not found"
        exit 1
    fi
    
    # Extract instance details from the launch script output
    local instructions_file="ec2-deployment-instructions.txt"
    if [ ! -f "$instructions_file" ]; then
        print_error "Could not find deployment instructions file"
        exit 1
    fi
    
    local public_ip=$(grep "Public IP:" "$instructions_file" | awk '{print $3}')
    local instance_id=$(grep "Instance ID:" "$instructions_file" | awk '{print $3}')
    
    if [ -z "$public_ip" ]; then
        print_error "Could not extract public IP from deployment instructions"
        exit 1
    fi
    
    print_success "Instance launched with IP: $public_ip"
    
    # Step 2: Wait for instance to be fully ready
    print_status "Step 2: Waiting for instance to be ready for SSH..."
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if ssh -i ~/.ssh/${key_name}.pem -o ConnectTimeout=10 -o StrictHostKeyChecking=no ubuntu@${public_ip} "echo 'ready'" &>/dev/null; then
            break
        fi
        attempt=$((attempt + 1))
        echo "Waiting... (attempt $attempt/$max_attempts)"
        sleep 10
    done
    
    if [ $attempt -eq $max_attempts ]; then
        print_error "Could not connect to instance via SSH"
        exit 1
    fi
    
    print_success "Instance is ready for deployment"
    
    # Step 3: Upload and run deployment script
    print_status "Step 3: Uploading deployment files..."
    
    # Create temporary directory on instance
    ssh -i ~/.ssh/${key_name}.pem ubuntu@${public_ip} "mkdir -p ~/tge-monitor-deploy"
    
    # Upload necessary files
    scp -i ~/.ssh/${key_name}.pem deploy-ec2-automated.sh ubuntu@${public_ip}:~/tge-monitor-deploy/
    scp -i ~/.ssh/${key_name}.pem -r . ubuntu@${public_ip}:~/tge-monitor-deploy/
    
    print_success "Files uploaded"
    
    # Step 4: Run automated deployment
    print_status "Step 4: Running automated deployment on instance..."
    print_warning "This may take 10-15 minutes. Please wait..."
    
    ssh -i ~/.ssh/${key_name}.pem ubuntu@${public_ip} "
        cd ~/tge-monitor-deploy
        chmod +x deploy-ec2-automated.sh
        echo 'y' | ./deploy-ec2-automated.sh
    "
    
    if [ $? -eq 0 ]; then
        print_success "🎉 Deployment completed successfully!"
    else
        print_error "Deployment failed. Check the logs on the instance."
        exit 1
    fi
    
    # Step 5: Display final information
    echo ""
    echo "==============================================================================="
    echo "                           DEPLOYMENT COMPLETE!"
    echo "==============================================================================="
    echo ""
    echo "🌐 Your TGE Monitor System is now running at:"
    echo "   • API Documentation: http://${public_ip}/docs"
    echo "   • Health Check:      http://${public_ip}/health"
    echo "   • WebSocket:         ws://${public_ip}/ws"
    echo ""
    echo "🔧 To access your instance:"
    echo "   ssh -i ~/.ssh/${key_name}.pem ubuntu@${public_ip}"
    echo ""
    echo "📊 Check system status:"
    echo "   sudo systemctl status tge-monitor-api"
    echo "   sudo systemctl status tge-monitor-worker"
    echo ""
    echo "⚙️  Configure credentials:"
    echo "   sudo vim /opt/tge-monitor/.env"
    echo ""
    echo "📋 View deployment credentials:"
    echo "   cat /opt/tge-monitor/DEPLOYMENT_CREDENTIALS.txt"
    echo ""
    echo "🏆 Your Enhanced TGE Monitor System is ready!"
    echo "==============================================================================="
}

main "$@"