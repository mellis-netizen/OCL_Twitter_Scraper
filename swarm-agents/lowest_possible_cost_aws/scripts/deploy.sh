#!/bin/bash
# Ultra-Low-Cost TGE Swarm Deployment Script
# Cost Optimization Engineer: Claude

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TERRAFORM_DIR="$PROJECT_ROOT/terraform"
CONFIG_DIR="$PROJECT_ROOT/config"

# Default values
AWS_REGION="us-east-1"
ENVIRONMENT="cost-optimized"
PROJECT_NAME="tge-swarm"
AUTO_SHUTDOWN_ENABLED="true"
ENABLE_MONITORING="true"
ENABLE_S3_BACKUPS="false"

# Function to show usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy TGE Swarm with ultra-low-cost configuration to AWS.

OPTIONS:
    -r, --region REGION          AWS region (default: us-east-1)
    -e, --environment ENV        Environment name (default: cost-optimized)
    -k, --key-name KEY          AWS EC2 Key Pair name (required)
    -d, --domain DOMAIN         Domain name for SSL certificate
    --alert-email EMAIL         Email for cost and system alerts
    --cost-threshold AMOUNT     Monthly cost threshold in USD (default: 150)
    --enable-s3-backups         Enable S3 backups (adds cost)
    --disable-auto-shutdown     Disable auto-shutdown feature
    --disable-monitoring        Disable monitoring stack
    --dry-run                   Show what would be deployed without executing
    -h, --help                  Show this help message

EXAMPLES:
    $0 --key-name my-aws-key --domain myapp.com --alert-email admin@myapp.com
    $0 --key-name my-key --disable-auto-shutdown --cost-threshold 100
    $0 --key-name my-key --enable-s3-backups --region us-west-2

COST OPTIMIZATION FEATURES:
    - Spot instances with interruption handling
    - Single AZ deployment
    - Consolidated services in minimal containers
    - Auto-shutdown during off-hours
    - Basic monitoring only
    - Local backups by default
    - Aggressive resource limits

ESTIMATED MONTHLY COST: \$35-45 (excluding data transfer)
EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -r|--region)
                AWS_REGION="$2"
                shift 2
                ;;
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -k|--key-name)
                KEY_NAME="$2"
                shift 2
                ;;
            -d|--domain)
                DOMAIN_NAME="$2"
                shift 2
                ;;
            --alert-email)
                ALERT_EMAIL="$2"
                shift 2
                ;;
            --cost-threshold)
                COST_THRESHOLD="$2"
                shift 2
                ;;
            --enable-s3-backups)
                ENABLE_S3_BACKUPS="true"
                shift
                ;;
            --disable-auto-shutdown)
                AUTO_SHUTDOWN_ENABLED="false"
                shift
                ;;
            --disable-monitoring)
                ENABLE_MONITORING="false"
                shift
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    # Validate required parameters
    if [ -z "$KEY_NAME" ]; then
        error "AWS Key Pair name is required. Use --key-name option."
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."

    # Check if required tools are installed
    local required_tools=("terraform" "aws" "docker" "docker-compose")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            error "$tool is not installed or not in PATH"
            exit 1
        fi
    done

    # Check AWS credentials
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        error "AWS credentials not configured. Run 'aws configure' first."
        exit 1
    fi

    # Check Terraform version
    local tf_version=$(terraform version -json | jq -r '.terraform_version')
    log "Using Terraform version: $tf_version"

    # Check AWS region
    if ! aws ec2 describe-regions --region-names "$AWS_REGION" >/dev/null 2>&1; then
        error "Invalid AWS region: $AWS_REGION"
        exit 1
    fi

    # Check EC2 key pair exists
    if ! aws ec2 describe-key-pairs --key-names "$KEY_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
        error "EC2 Key Pair '$KEY_NAME' not found in region $AWS_REGION"
        exit 1
    fi

    log "Prerequisites check passed"
}

# Estimate costs
estimate_costs() {
    info "Estimated Monthly Costs (USD):"
    echo "================================"
    echo "• Main Instance (t3.small spot):     ~\$4.50"
    echo "• Backup Instance (t3.nano):         ~\$3.80"
    echo "• EBS Storage (20GB gp3):            ~\$2.00"
    echo "• Application Load Balancer:         ~\$16.20"
    echo "• Data Transfer (estimated):         ~\$5.00"
    echo "• CloudWatch Basic:                  ~\$3.50"
    echo "• SNS Notifications:                 ~\$0.50"
    echo "• Lambda (cost optimizer):           ~\$0.20"
    
    if [ "$ENABLE_S3_BACKUPS" = "true" ]; then
        echo "• S3 Backups (optional):             ~\$1.00"
    else
        echo "• S3 Backups:                        \$0.00 (disabled)"
    fi
    
    echo "--------------------------------"
    echo "• TOTAL ESTIMATED:                   ~\$35-45/month"
    echo "================================"
    echo ""
    warn "Actual costs may vary based on usage patterns"
    echo ""
}

# Prepare Terraform variables
prepare_terraform_vars() {
    log "Preparing Terraform variables..."

    local tfvars_file="$TERRAFORM_DIR/terraform.tfvars"
    
    cat > "$tfvars_file" << EOF
# TGE Swarm Ultra-Low-Cost Deployment Variables
# Generated by deploy script on $(date)

# Basic Configuration
aws_region    = "$AWS_REGION"
environment   = "$ENVIRONMENT"
project_name  = "$PROJECT_NAME"
key_name      = "$KEY_NAME"

# Cost Optimization Settings
auto_shutdown_enabled       = $AUTO_SHUTDOWN_ENABLED
auto_shutdown_schedule      = "0 22 * * *"    # 10 PM UTC
auto_startup_schedule       = "0 6 * * 1-5"   # 6 AM UTC, weekdays
enable_detailed_monitoring  = false
storage_size               = 20
backup_retention_days      = 7

# Features
enable_monitoring_stack    = $ENABLE_MONITORING
enable_backup_to_s3       = $ENABLE_S3_BACKUPS

# Domain and SSL (optional)
EOF

    if [ -n "$DOMAIN_NAME" ]; then
        echo "domain_name                = \"$DOMAIN_NAME\"" >> "$tfvars_file"
        echo "manage_dns_with_route53    = false  # Set to true if using Route53" >> "$tfvars_file"
    fi

    if [ -n "$ALERT_EMAIL" ]; then
        echo "alert_email                = \"$ALERT_EMAIL\"" >> "$tfvars_file"
    fi

    if [ -n "$COST_THRESHOLD" ]; then
        echo "cost_threshold             = $COST_THRESHOLD" >> "$tfvars_file"
    fi

    echo "" >> "$tfvars_file"
    echo "# Security (restrict as needed)" >> "$tfvars_file"
    echo "allowed_cidr_blocks        = [\"0.0.0.0/0\"]  # CHANGE THIS IN PRODUCTION" >> "$tfvars_file"

    log "Terraform variables written to $tfvars_file"
}

# Build Docker images
build_docker_images() {
    log "Building Docker images..."

    cd "$PROJECT_ROOT"

    # Build the all-in-one image
    docker build -t tge-swarm-all-in-one:cost-optimized -f docker/Dockerfile.all-in-one .

    # Build monitoring image if enabled
    if [ "$ENABLE_MONITORING" = "true" ]; then
        log "Building monitoring image..."
        # This would build a combined Prometheus + Grafana image
        # For now, we'll use standard images in docker-compose
    fi

    log "Docker images built successfully"
}

# Deploy infrastructure
deploy_infrastructure() {
    log "Deploying infrastructure with Terraform..."

    cd "$TERRAFORM_DIR"

    if [ "$DRY_RUN" = "true" ]; then
        info "DRY RUN: Would execute the following Terraform commands:"
        echo "terraform init"
        echo "terraform plan -var-file=terraform.tfvars"
        echo "terraform apply -var-file=terraform.tfvars"
        return 0
    fi

    # Initialize Terraform
    terraform init

    # Plan deployment
    log "Creating Terraform plan..."
    terraform plan -var-file=terraform.tfvars -out=tfplan

    # Show plan summary
    info "Terraform will create the following resources:"
    terraform show -json tfplan | jq -r '.planned_values.root_module.resources[].type' | sort | uniq -c

    # Confirm deployment
    echo ""
    read -p "Proceed with deployment? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        warn "Deployment cancelled by user"
        exit 0
    fi

    # Apply changes
    log "Applying Terraform changes..."
    terraform apply tfplan

    # Get outputs
    log "Deployment completed! Getting outputs..."
    terraform output -json > "$PROJECT_ROOT/deployment-outputs.json"

    # Display key information
    local lb_dns=$(terraform output -raw load_balancer_dns)
    local cost_info=$(terraform output -json estimated_monthly_cost)

    info "Deployment Summary:"
    echo "================================"
    echo "Load Balancer DNS: $lb_dns"
    echo "TGE Swarm API: https://$lb_dns/api"
    
    if [ "$ENABLE_MONITORING" = "true" ]; then
        echo "Grafana Dashboard: https://$lb_dns/grafana"
    fi
    
    echo ""
    echo "Cost Information:"
    echo "$cost_info" | jq -r 'to_entries[] | "\(.key): \(.value)"'
    echo "================================"
}

# Deploy application
deploy_application() {
    log "Deploying application containers..."

    cd "$PROJECT_ROOT"

    if [ "$DRY_RUN" = "true" ]; then
        info "DRY RUN: Would deploy Docker containers to EC2 instances"
        return 0
    fi

    # The application deployment happens automatically via user-data scripts
    # We just need to wait for it to complete and verify

    local lb_dns=$(cd "$TERRAFORM_DIR" && terraform output -raw load_balancer_dns)
    
    log "Waiting for application to become available..."
    log "This may take 5-10 minutes for initial startup..."

    local timeout=600  # 10 minutes
    local count=0
    
    while [ $count -lt $timeout ]; do
        if curl -f --connect-timeout 10 "https://$lb_dns/health" >/dev/null 2>&1; then
            log "Application is now available!"
            break
        fi
        
        sleep 30
        count=$((count + 30))
        echo -n "."
    done
    
    if [ $count -ge $timeout ]; then
        error "Application did not become available within 10 minutes"
        error "Check the EC2 instance logs for details"
        exit 1
    fi

    log "Application deployment completed successfully"
}

# Set up monitoring alerts
setup_monitoring() {
    if [ "$ALERT_EMAIL" ] && [ "$DRY_RUN" != "true" ]; then
        log "Setting up monitoring alerts..."
        
        # Subscribe to SNS topic for alerts
        local sns_topic_arn=$(cd "$TERRAFORM_DIR" && terraform output -raw sns_topic_arn)
        
        aws sns subscribe \
            --region "$AWS_REGION" \
            --topic-arn "$sns_topic_arn" \
            --protocol email \
            --notification-endpoint "$ALERT_EMAIL"
            
        info "Please check your email and confirm the SNS subscription"
    fi
}

# Main deployment function
main() {
    log "Starting TGE Swarm Ultra-Low-Cost Deployment"
    log "============================================="

    parse_args "$@"
    
    info "Deployment Configuration:"
    echo "Region: $AWS_REGION"
    echo "Environment: $ENVIRONMENT"
    echo "Key Name: $KEY_NAME"
    echo "Domain: ${DOMAIN_NAME:-"(not set)"}"
    echo "Alert Email: ${ALERT_EMAIL:-"(not set)"}"
    echo "Auto-shutdown: $AUTO_SHUTDOWN_ENABLED"
    echo "S3 Backups: $ENABLE_S3_BACKUPS"
    echo "Monitoring: $ENABLE_MONITORING"
    echo "Dry Run: ${DRY_RUN:-"false"}"
    echo ""

    estimate_costs
    
    if [ "$DRY_RUN" != "true" ]; then
        read -p "Continue with deployment? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            warn "Deployment cancelled by user"
            exit 0
        fi
    fi

    check_prerequisites
    prepare_terraform_vars
    build_docker_images
    deploy_infrastructure
    deploy_application
    setup_monitoring

    log "============================================="
    log "TGE Swarm Ultra-Low-Cost Deployment Complete!"
    
    if [ "$DRY_RUN" != "true" ]; then
        local lb_dns=$(cd "$TERRAFORM_DIR" && terraform output -raw load_balancer_dns)
        echo ""
        info "Access your TGE Swarm deployment at:"
        echo "• Application: https://$lb_dns"
        echo "• API: https://$lb_dns/api"
        
        if [ "$ENABLE_MONITORING" = "true" ]; then
            echo "• Monitoring: https://$lb_dns/grafana"
        fi
        
        echo ""
        info "Cost optimization features active:"
        echo "• Spot instances with interruption handling"
        echo "• Auto-shutdown: $AUTO_SHUTDOWN_ENABLED"
        echo "• Cost monitoring and alerts"
        echo "• Consolidated services for minimal resource usage"
        
        if [ "$ALERT_EMAIL" ]; then
            echo ""
            warn "Don't forget to confirm your email subscription for alerts!"
        fi
    fi
}

# Run main function with all arguments
main "$@"