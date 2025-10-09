#!/bin/bash
# TGE Swarm AWS Deployment Script
# Comprehensive deployment automation for AWS infrastructure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR"
STATE_BUCKET=""
STATE_KEY="production/terraform.tfstate"
STATE_REGION="us-west-2"
LOCK_TABLE=""

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_usage() {
    cat << EOF
TGE Swarm AWS Deployment Script

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    init        Initialize Terraform backend and providers
    validate    Validate Terraform configuration
    plan        Create and show Terraform execution plan
    apply       Apply Terraform configuration
    destroy     Destroy Terraform-managed infrastructure
    output      Show Terraform outputs
    refresh     Refresh Terraform state
    upgrade     Upgrade Terraform providers
    clean       Clean Terraform cache and temporary files

Options:
    -h, --help              Show this help message
    -v, --verbose           Enable verbose output
    -f, --force             Force operation without confirmation
    -t, --target RESOURCE   Target specific resource
    -b, --backend-config    Configure remote backend
    --state-bucket BUCKET   S3 bucket for state storage
    --state-key KEY        S3 key for state file
    --state-region REGION   AWS region for state bucket
    --lock-table TABLE     DynamoDB table for state locking

Examples:
    $0 init --state-bucket my-terraform-state --lock-table terraform-locks
    $0 plan
    $0 apply --force
    $0 destroy --target aws_instance.swarm_queen
    $0 output connection_info
EOF
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if terraform is installed
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform is not installed. Please install Terraform first."
        exit 1
    fi
    
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install AWS CLI first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    # Check if terraform.tfvars exists
    if [ ! -f "$TERRAFORM_DIR/terraform.tfvars" ]; then
        log_warning "terraform.tfvars not found. Please copy terraform.tfvars.example and customize it."
        log_info "cp terraform.tfvars.example terraform.tfvars"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

setup_backend() {
    if [ -n "$STATE_BUCKET" ]; then
        log_info "Configuring Terraform backend..."
        
        cat > "$TERRAFORM_DIR/backend.tf" << EOF
terraform {
  backend "s3" {
    bucket         = "$STATE_BUCKET"
    key            = "$STATE_KEY"
    region         = "$STATE_REGION"
    encrypt        = true
    dynamodb_table = "$LOCK_TABLE"
  }
}
EOF
        
        log_success "Backend configuration created"
    fi
}

terraform_init() {
    log_info "Initializing Terraform..."
    cd "$TERRAFORM_DIR"
    
    terraform init -upgrade
    
    log_success "Terraform initialized successfully"
}

terraform_validate() {
    log_info "Validating Terraform configuration..."
    cd "$TERRAFORM_DIR"
    
    terraform validate
    terraform fmt -check
    
    log_success "Terraform configuration is valid"
}

terraform_plan() {
    log_info "Creating Terraform execution plan..."
    cd "$TERRAFORM_DIR"
    
    local plan_file="terraform.plan"
    local target_args=""
    
    if [ -n "$TARGET_RESOURCE" ]; then
        target_args="-target=$TARGET_RESOURCE"
    fi
    
    terraform plan $target_args -out="$plan_file"
    
    log_success "Terraform plan created: $plan_file"
    log_info "Review the plan above before applying"
}

terraform_apply() {
    log_info "Applying Terraform configuration..."
    cd "$TERRAFORM_DIR"
    
    local plan_file="terraform.plan"
    local auto_approve=""
    local target_args=""
    
    if [ "$FORCE" = true ]; then
        auto_approve="-auto-approve"
    fi
    
    if [ -n "$TARGET_RESOURCE" ]; then
        target_args="-target=$TARGET_RESOURCE"
    fi
    
    if [ -f "$plan_file" ] && [ -z "$target_args" ]; then
        terraform apply "$plan_file"
    else
        terraform apply $auto_approve $target_args
    fi
    
    log_success "Terraform configuration applied successfully"
    
    # Show important outputs
    log_info "Important connection information:"
    terraform output connection_info
}

terraform_destroy() {
    log_error "DANGER: This will destroy ALL infrastructure!"
    
    if [ "$FORCE" != true ]; then
        read -p "Are you sure you want to destroy the infrastructure? Type 'yes' to confirm: " confirm
        if [ "$confirm" != "yes" ]; then
            log_info "Destruction cancelled"
            exit 0
        fi
    fi
    
    log_info "Destroying Terraform-managed infrastructure..."
    cd "$TERRAFORM_DIR"
    
    local target_args=""
    
    if [ -n "$TARGET_RESOURCE" ]; then
        target_args="-target=$TARGET_RESOURCE"
    fi
    
    terraform destroy -auto-approve $target_args
    
    log_success "Infrastructure destroyed"
}

terraform_output() {
    log_info "Showing Terraform outputs..."
    cd "$TERRAFORM_DIR"
    
    if [ -n "$1" ]; then
        terraform output "$1"
    else
        terraform output
    fi
}

terraform_refresh() {
    log_info "Refreshing Terraform state..."
    cd "$TERRAFORM_DIR"
    
    terraform refresh
    
    log_success "Terraform state refreshed"
}

terraform_upgrade() {
    log_info "Upgrading Terraform providers..."
    cd "$TERRAFORM_DIR"
    
    terraform init -upgrade
    
    log_success "Terraform providers upgraded"
}

clean_terraform() {
    log_info "Cleaning Terraform cache and temporary files..."
    cd "$TERRAFORM_DIR"
    
    rm -rf .terraform/
    rm -f .terraform.lock.hcl
    rm -f terraform.plan
    rm -f backend.tf
    
    log_success "Terraform cache cleaned"
}

post_deployment_checks() {
    log_info "Running post-deployment health checks..."
    
    # Get ALB DNS name
    ALB_DNS=$(terraform output -raw load_balancer_dns_name 2>/dev/null || echo "")
    
    if [ -n "$ALB_DNS" ]; then
        log_info "Waiting for load balancer to be ready..."
        sleep 30
        
        # Check load balancer health
        if curl -f -s --max-time 30 "http://$ALB_DNS/health" > /dev/null; then
            log_success "Load balancer is responding"
        else
            log_warning "Load balancer health check failed - this is normal during initial deployment"
        fi
    fi
    
    # Show connection information
    log_info "Deployment completed! Connection information:"
    terraform output connection_info 2>/dev/null || log_warning "Connection info not available yet"
}

# Parse command line arguments
COMMAND=""
VERBOSE=false
FORCE=false
TARGET_RESOURCE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        init|validate|plan|apply|destroy|output|refresh|upgrade|clean)
            COMMAND="$1"
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -t|--target)
            TARGET_RESOURCE="$2"
            shift 2
            ;;
        --state-bucket)
            STATE_BUCKET="$2"
            shift 2
            ;;
        --state-key)
            STATE_KEY="$2"
            shift 2
            ;;
        --state-region)
            STATE_REGION="$2"
            shift 2
            ;;
        --lock-table)
            LOCK_TABLE="$2"
            shift 2
            ;;
        *)
            if [ -z "$COMMAND" ]; then
                COMMAND="$1"
            else
                log_error "Unknown option: $1"
                show_usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Enable verbose output if requested
if [ "$VERBOSE" = true ]; then
    set -x
fi

# Main execution
log_info "TGE Swarm AWS Deployment Script"
log_info "Command: $COMMAND"

case $COMMAND in
    init)
        check_prerequisites
        setup_backend
        terraform_init
        ;;
    validate)
        check_prerequisites
        terraform_validate
        ;;
    plan)
        check_prerequisites
        terraform_plan
        ;;
    apply)
        check_prerequisites
        terraform_apply
        post_deployment_checks
        ;;
    destroy)
        check_prerequisites
        terraform_destroy
        ;;
    output)
        terraform_output "$2"
        ;;
    refresh)
        check_prerequisites
        terraform_refresh
        ;;
    upgrade)
        check_prerequisites
        terraform_upgrade
        ;;
    clean)
        clean_terraform
        ;;
    "")
        log_error "No command specified"
        show_usage
        exit 1
        ;;
    *)
        log_error "Unknown command: $COMMAND"
        show_usage
        exit 1
        ;;
esac

log_success "Operation completed successfully"