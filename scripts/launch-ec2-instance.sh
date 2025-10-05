#!/bin/bash

# ===============================================================================
# Enhanced TGE Monitor System - EC2 Instance Launch Script
# ===============================================================================
# 
# This script launches a new EC2 instance and sets it up for TGE Monitor deployment
# Run this script from your local machine with AWS CLI configured
#
# Prerequisites:
# - AWS CLI installed and configured
# - SSH key pair created in your AWS region
# - Appropriate IAM permissions for EC2
#
# Usage: ./launch-ec2-instance.sh [key-name] [region]
# ===============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default configuration
DEFAULT_REGION="us-east-1"
DEFAULT_INSTANCE_TYPE="t3.large"
DEFAULT_AMI_NAME="ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if AWS CLI is configured
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed"
        print_error "Please install AWS CLI: https://aws.amazon.com/cli/"
        exit 1
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS CLI is not configured"
        print_error "Please run: aws configure"
        exit 1
    fi
    
    print_success "AWS CLI is configured"
}

# Function to get latest Ubuntu AMI
get_latest_ubuntu_ami() {
    local region="$1"
    print_status "Finding latest Ubuntu 22.04 LTS AMI in $region..."
    
    local ami_id=$(aws ec2 describe-images \
        --region "$region" \
        --owners 099720109477 \
        --filters "Name=name,Values=$DEFAULT_AMI_NAME" \
        --query 'Images[*].[ImageId,CreationDate,Name]' \
        --output text | sort -k2 -r | head -n1 | cut -f1)
    
    if [ -z "$ami_id" ]; then
        print_error "Could not find Ubuntu 22.04 LTS AMI in region $region"
        exit 1
    fi
    
    print_success "Found AMI: $ami_id"
    echo "$ami_id"
}

# Function to create security group
create_security_group() {
    local region="$1"
    local vpc_id="$2"
    local sg_name="tge-monitor-sg-$(date +%s)"
    
    print_status "Creating security group: $sg_name"
    
    # Create security group
    local sg_id=$(aws ec2 create-security-group \
        --region "$region" \
        --group-name "$sg_name" \
        --description "Security group for TGE Monitor System" \
        --vpc-id "$vpc_id" \
        --query 'GroupId' \
        --output text)
    
    if [ -z "$sg_id" ]; then
        print_error "Failed to create security group"
        exit 1
    fi
    
    # Add inbound rules
    print_status "Adding security group rules..."
    
    # SSH access (port 22)
    aws ec2 authorize-security-group-ingress \
        --region "$region" \
        --group-id "$sg_id" \
        --protocol tcp \
        --port 22 \
        --cidr 0.0.0.0/0 > /dev/null
    
    # HTTP access (port 80)
    aws ec2 authorize-security-group-ingress \
        --region "$region" \
        --group-id "$sg_id" \
        --protocol tcp \
        --port 80 \
        --cidr 0.0.0.0/0 > /dev/null
    
    # HTTPS access (port 443)
    aws ec2 authorize-security-group-ingress \
        --region "$region" \
        --group-id "$sg_id" \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0 > /dev/null
    
    # API access (port 8000) - restricted to your IP
    local my_ip=$(curl -s http://checkip.amazonaws.com)
    if [ -n "$my_ip" ]; then
        aws ec2 authorize-security-group-ingress \
            --region "$region" \
            --group-id "$sg_id" \
            --protocol tcp \
            --port 8000 \
            --cidr "${my_ip}/32" > /dev/null
        print_status "Added API access for your IP: $my_ip"
    fi
    
    print_success "Security group created: $sg_id"
    echo "$sg_id"
}

# Function to create user data script
create_user_data() {
    cat << 'EOF'
#!/bin/bash
# Initial EC2 setup for TGE Monitor deployment

# Update system
apt-get update
apt-get upgrade -y

# Install git for repository cloning
apt-get install -y git

# Create log file
touch /var/log/user-data.log
chmod 644 /var/log/user-data.log

# Log start time
echo "User data script started at $(date)" >> /var/log/user-data.log

# Set timezone to PST
timedatectl set-timezone America/Los_Angeles

# Configure automatic security updates
echo 'Unattended-Upgrade::Automatic-Reboot "false";' >> /etc/apt/apt.conf.d/50unattended-upgrades

# Log completion
echo "User data script completed at $(date)" >> /var/log/user-data.log
EOF
}

# Function to launch EC2 instance
launch_instance() {
    local key_name="$1"
    local region="$2"
    local ami_id="$3"
    local sg_id="$4"
    local subnet_id="$5"
    
    print_status "Launching EC2 instance..."
    
    # Create user data
    local user_data=$(create_user_data | base64 -w 0)
    
    # Launch instance
    local instance_id=$(aws ec2 run-instances \
        --region "$region" \
        --image-id "$ami_id" \
        --count 1 \
        --instance-type "$DEFAULT_INSTANCE_TYPE" \
        --key-name "$key_name" \
        --security-group-ids "$sg_id" \
        --subnet-id "$subnet_id" \
        --user-data "$user_data" \
        --block-device-mappings '[
            {
                "DeviceName": "/dev/sda1",
                "Ebs": {
                    "VolumeSize": 30,
                    "VolumeType": "gp3",
                    "DeleteOnTermination": true
                }
            }
        ]' \
        --tag-specifications 'ResourceType=instance,Tags=[
            {Key=Name,Value=TGE-Monitor-System},
            {Key=Project,Value=TGE-Monitor},
            {Key=Environment,Value=Production}
        ]' \
        --query 'Instances[0].InstanceId' \
        --output text)
    
    if [ -z "$instance_id" ]; then
        print_error "Failed to launch instance"
        exit 1
    fi
    
    print_success "Instance launched: $instance_id"
    echo "$instance_id"
}

# Function to wait for instance to be ready
wait_for_instance() {
    local instance_id="$1"
    local region="$2"
    
    print_status "Waiting for instance to be running..."
    
    aws ec2 wait instance-running \
        --region "$region" \
        --instance-ids "$instance_id"
    
    print_status "Waiting for status checks to pass..."
    
    aws ec2 wait instance-status-ok \
        --region "$region" \
        --instance-ids "$instance_id"
    
    print_success "Instance is ready!"
}

# Function to get instance details
get_instance_details() {
    local instance_id="$1"
    local region="$2"
    
    aws ec2 describe-instances \
        --region "$region" \
        --instance-ids "$instance_id" \
        --query 'Reservations[0].Instances[0].[PublicIpAddress,PrivateIpAddress,InstanceType,State.Name]' \
        --output text
}

# Function to create deployment instructions
create_deployment_instructions() {
    local instance_id="$1"
    local public_ip="$2"
    local key_name="$3"
    local region="$4"
    
    local instructions_file="ec2-deployment-instructions.txt"
    
    cat > "$instructions_file" << EOF
===============================================================================
                    TGE MONITOR EC2 DEPLOYMENT INSTRUCTIONS
===============================================================================

Instance Details:
  Instance ID: $instance_id
  Public IP:   $public_ip
  Region:      $region
  Key Name:    $key_name

===============================================================================
STEP 1: CONNECT TO YOUR INSTANCE
===============================================================================

ssh -i ~/.ssh/$key_name.pem ubuntu@$public_ip

Note: Make sure your key file has correct permissions:
chmod 400 ~/.ssh/$key_name.pem

===============================================================================
STEP 2: UPLOAD DEPLOYMENT SCRIPT
===============================================================================

From your local machine, copy the repository to the instance:

# Option A: Clone from GitHub (if repository is public)
ssh -i ~/.ssh/$key_name.pem ubuntu@$public_ip "git clone https://github.com/yourusername/OCL_Twitter_Scraper.git"

# Option B: Upload local files
scp -i ~/.ssh/$key_name.pem -r . ubuntu@$public_ip:~/OCL_Twitter_Scraper/

===============================================================================
STEP 3: RUN AUTOMATED DEPLOYMENT
===============================================================================

Once connected to the instance:

cd OCL_Twitter_Scraper
chmod +x deploy-ec2-automated.sh
./deploy-ec2-automated.sh

===============================================================================
STEP 4: ACCESS YOUR APPLICATION
===============================================================================

After deployment completes:

  • API Documentation: http://$public_ip/docs
  • Health Check:      http://$public_ip/health
  • WebSocket:         ws://$public_ip/ws

===============================================================================
STEP 5: CONFIGURE CREDENTIALS
===============================================================================

1. Edit environment file:
   sudo vim /opt/tge-monitor/.env

2. Configure email settings:
   SMTP_SERVER=your-smtp-server
   EMAIL_USER=your-email
   EMAIL_PASSWORD=your-password

3. Add Twitter API credentials (optional):
   TWITTER_BEARER_TOKEN=your-token

===============================================================================
TROUBLESHOOTING
===============================================================================

• Check deployment logs: tail -f /tmp/tge-monitor-deployment.log
• View service status: sudo systemctl status tge-monitor-*
• Check application logs: tail -f /opt/tge-monitor/logs/*.log
• Run health check: /opt/tge-monitor/health_check.sh

===============================================================================
SECURITY REMINDERS
===============================================================================

• Change default passwords (see /opt/tge-monitor/DEPLOYMENT_CREDENTIALS.txt)
• Setup SSL certificate: sudo certbot --nginx -d your-domain.com
• Review firewall rules: sudo ufw status
• Enable automatic backups offsite

===============================================================================
INSTANCE MANAGEMENT
===============================================================================

Start instance:  aws ec2 start-instances --instance-ids $instance_id --region $region
Stop instance:   aws ec2 stop-instances --instance-ids $instance_id --region $region
Terminate:       aws ec2 terminate-instances --instance-ids $instance_id --region $region

For support, refer to the EC2_DEPLOYMENT_GUIDE_COMPLETE.md file.

Generated on: $(date)
EOF

    print_success "Deployment instructions saved to: $instructions_file"
}

# Main function
main() {
    local key_name="$1"
    local region="${2:-$DEFAULT_REGION}"
    
    echo "==============================================================================="
    echo "          Enhanced TGE Monitor System - EC2 Instance Launcher"
    echo "==============================================================================="
    
    # Validate inputs
    if [ -z "$key_name" ]; then
        print_error "Usage: $0 <key-name> [region]"
        print_error "Example: $0 my-key-pair us-east-1"
        exit 1
    fi
    
    print_status "Launching EC2 instance for TGE Monitor System"
    print_status "Key pair: $key_name"
    print_status "Region: $region"
    print_status "Instance type: $DEFAULT_INSTANCE_TYPE"
    echo ""
    
    # Check prerequisites
    check_aws_cli
    
    # Verify key pair exists
    if ! aws ec2 describe-key-pairs --region "$region" --key-names "$key_name" &> /dev/null; then
        print_error "Key pair '$key_name' not found in region '$region'"
        print_error "Create a key pair first: aws ec2 create-key-pair --key-name $key_name --query 'KeyMaterial' --output text > ~/.ssh/$key_name.pem"
        exit 1
    fi
    
    # Get default VPC
    print_status "Finding default VPC..."
    local vpc_id=$(aws ec2 describe-vpcs \
        --region "$region" \
        --filters "Name=isDefault,Values=true" \
        --query 'Vpcs[0].VpcId' \
        --output text)
    
    if [ "$vpc_id" = "None" ] || [ -z "$vpc_id" ]; then
        print_error "No default VPC found in region $region"
        exit 1
    fi
    
    # Get default subnet
    local subnet_id=$(aws ec2 describe-subnets \
        --region "$region" \
        --filters "Name=vpc-id,Values=$vpc_id" "Name=default-for-az,Values=true" \
        --query 'Subnets[0].SubnetId' \
        --output text)
    
    if [ "$subnet_id" = "None" ] || [ -z "$subnet_id" ]; then
        print_error "No default subnet found"
        exit 1
    fi
    
    print_success "Using VPC: $vpc_id, Subnet: $subnet_id"
    
    # Get AMI
    local ami_id=$(get_latest_ubuntu_ami "$region")
    
    # Create security group
    local sg_id=$(create_security_group "$region" "$vpc_id")
    
    # Launch instance
    local instance_id=$(launch_instance "$key_name" "$region" "$ami_id" "$sg_id" "$subnet_id")
    
    # Wait for instance to be ready
    wait_for_instance "$instance_id" "$region"
    
    # Get instance details
    local instance_details=$(get_instance_details "$instance_id" "$region")
    local public_ip=$(echo "$instance_details" | cut -f1)
    local private_ip=$(echo "$instance_details" | cut -f2)
    local instance_type=$(echo "$instance_details" | cut -f3)
    local state=$(echo "$instance_details" | cut -f4)
    
    # Display results
    echo ""
    print_success "🎉 EC2 Instance launched successfully!"
    echo ""
    echo "==============================================================================="
    echo "                            INSTANCE DETAILS"
    echo "==============================================================================="
    echo ""
    echo "Instance ID:      $instance_id"
    echo "Public IP:        $public_ip"
    echo "Private IP:       $private_ip"
    echo "Instance Type:    $instance_type"
    echo "Region:           $region"
    echo "Key Name:         $key_name"
    echo "AMI ID:           $ami_id"
    echo "Security Group:   $sg_id"
    echo "State:            $state"
    echo ""
    echo "==============================================================================="
    echo "                              NEXT STEPS"
    echo "==============================================================================="
    echo ""
    echo "1. Connect to your instance:"
    echo "   ssh -i ~/.ssh/$key_name.pem ubuntu@$public_ip"
    echo ""
    echo "2. Upload and run the deployment script:"
    echo "   scp -i ~/.ssh/$key_name.pem deploy-ec2-automated.sh ubuntu@$public_ip:~/"
    echo "   ssh -i ~/.ssh/$key_name.pem ubuntu@$public_ip"
    echo "   chmod +x deploy-ec2-automated.sh"
    echo "   ./deploy-ec2-automated.sh"
    echo ""
    echo "3. After deployment, access your application:"
    echo "   http://$public_ip/docs (API Documentation)"
    echo "   http://$public_ip/health (Health Check)"
    echo ""
    
    # Create detailed instructions file
    create_deployment_instructions "$instance_id" "$public_ip" "$key_name" "$region"
    
    echo "📁 Detailed instructions saved to: ec2-deployment-instructions.txt"
    echo ""
    echo "⚠️  Important: Save your instance details and configure security settings!"
    echo "==============================================================================="
}

# Run main function
main "$@"