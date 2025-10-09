#!/bin/bash

# TGE Swarm AWS EC2 Deployment Script
# Simple one-command deployment for AWS EC2

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration variables (edit these for your environment)
AWS_REGION="${AWS_REGION:-us-west-2}"
ENVIRONMENT="${ENVIRONMENT:-production}"
PROJECT_NAME="tge-swarm"
KEY_PAIR_NAME="tge-swarm-keypair"
TERRAFORM_STATE_BUCKET="tge-swarm-terraform-state-$(date +%s)"
TERRAFORM_LOCK_TABLE="tge-swarm-terraform-locks"

print_info "Starting TGE Swarm AWS Deployment"
print_info "================================="

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        print_error "Terraform is not installed. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Run 'aws configure' first."
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_warning "Docker not found. Some local testing features may not work."
    fi
    
    print_success "All prerequisites met!"
}

# Function to setup AWS resources
setup_aws_resources() {
    print_info "Setting up AWS resources..."
    
    # Create S3 bucket for Terraform state
    print_info "Creating S3 bucket for Terraform state..."
    if aws s3 mb "s3://${TERRAFORM_STATE_BUCKET}" --region "${AWS_REGION}" 2>/dev/null; then
        print_success "Created S3 bucket: ${TERRAFORM_STATE_BUCKET}"
    else
        print_warning "S3 bucket may already exist or name unavailable"
    fi
    
    # Enable versioning
    aws s3api put-bucket-versioning \
        --bucket "${TERRAFORM_STATE_BUCKET}" \
        --versioning-configuration Status=Enabled
    
    # Create DynamoDB table for state locking
    print_info "Creating DynamoDB table for Terraform locking..."
    if aws dynamodb create-table \
        --table-name "${TERRAFORM_LOCK_TABLE}" \
        --attribute-definitions AttributeName=LockID,AttributeType=S \
        --key-schema AttributeName=LockID,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --region "${AWS_REGION}" &> /dev/null; then
        print_success "Created DynamoDB table: ${TERRAFORM_LOCK_TABLE}"
    else
        print_warning "DynamoDB table may already exist"
    fi
    
    # Create EC2 key pair
    print_info "Creating EC2 key pair..."
    if aws ec2 create-key-pair \
        --key-name "${KEY_PAIR_NAME}" \
        --query 'KeyMaterial' \
        --output text > ~/.ssh/${KEY_PAIR_NAME}.pem 2>/dev/null; then
        chmod 400 ~/.ssh/${KEY_PAIR_NAME}.pem
        print_success "Created EC2 key pair: ${KEY_PAIR_NAME}"
        print_info "Private key saved to: ~/.ssh/${KEY_PAIR_NAME}.pem"
    else
        print_warning "Key pair may already exist"
    fi
}

# Function to configure Terraform
configure_terraform() {
    print_info "Configuring Terraform..."
    
    cd infrastructure/aws
    
    # Create terraform.tfvars from example
    if [ ! -f terraform.tfvars ]; then
        cp terraform.tfvars.example terraform.tfvars
        
        # Update with our values
        sed -i.bak "s/us-west-2/${AWS_REGION}/g" terraform.tfvars
        sed -i.bak "s/production/${ENVIRONMENT}/g" terraform.tfvars
        sed -i.bak "s/your-key-pair-name/${KEY_PAIR_NAME}/g" terraform.tfvars
        
        print_success "Created terraform.tfvars file"
        print_warning "Please review and update terraform.tfvars with your specific settings"
    else
        print_info "terraform.tfvars already exists, skipping creation"
    fi
    
    # Initialize Terraform
    print_info "Initializing Terraform..."
    terraform init \
        -backend-config="bucket=${TERRAFORM_STATE_BUCKET}" \
        -backend-config="key=${ENVIRONMENT}/terraform.tfstate" \
        -backend-config="region=${AWS_REGION}" \
        -backend-config="dynamodb_table=${TERRAFORM_LOCK_TABLE}"
    
    print_success "Terraform initialized successfully"
    
    cd ../..
}

# Function to deploy infrastructure
deploy_infrastructure() {
    print_info "Deploying infrastructure..."
    
    cd infrastructure/aws
    
    # Terraform plan
    print_info "Creating Terraform plan..."
    terraform plan -out=tfplan
    
    # Ask for confirmation
    echo ""
    print_warning "Review the Terraform plan above."
    read -p "Do you want to proceed with deployment? (y/N): " confirm
    
    if [[ $confirm =~ ^[Yy]$ ]]; then
        # Apply the plan
        print_info "Applying Terraform plan..."
        terraform apply tfplan
        
        print_success "Infrastructure deployed successfully!"
        
        # Show connection information
        echo ""
        print_info "Connection Information:"
        terraform output connection_info
        
    else
        print_info "Deployment cancelled by user"
        rm -f tfplan
        exit 0
    fi
    
    cd ../..
}

# Function to verify deployment
verify_deployment() {
    print_info "Verifying deployment..."
    
    cd infrastructure/aws
    
    # Get load balancer DNS
    LB_DNS=$(terraform output -raw load_balancer_dns_name 2>/dev/null || echo "Not available")
    
    if [ "$LB_DNS" != "Not available" ]; then
        print_info "Testing load balancer connectivity..."
        
        # Wait a bit for services to start
        sleep 30
        
        # Test HTTP endpoint
        if curl -s --max-time 10 "http://${LB_DNS}/health" > /dev/null; then
            print_success "Load balancer is responding!"
        else
            print_warning "Load balancer not yet responding. This is normal for new deployments."
            print_info "Services may take 5-10 minutes to fully start up."
        fi
        
        echo ""
        print_success "Deployment completed!"
        print_info "Dashboard URL: http://${LB_DNS}"
        print_info "API URL: http://${LB_DNS}/api"
        print_info "Grafana URL: http://${LB_DNS}:3000"
        
    else
        print_warning "Could not retrieve load balancer DNS. Check Terraform outputs."
    fi
    
    cd ../..
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "OPTIONS:"
    echo "  --region REGION     AWS region (default: us-west-2)"
    echo "  --environment ENV   Environment name (default: production)"
    echo "  --plan-only         Only create Terraform plan, don't apply"
    echo "  --destroy           Destroy existing infrastructure"
    echo "  --status            Show deployment status"
    echo "  --help              Show this help message"
    echo ""
    echo "EXAMPLES:"
    echo "  $0                                 # Deploy with defaults"
    echo "  $0 --region us-east-1              # Deploy to us-east-1"
    echo "  $0 --environment staging           # Deploy staging environment"
    echo "  $0 --plan-only                     # Just create plan"
    echo "  $0 --destroy                       # Destroy infrastructure"
    echo "  $0 --status                        # Check status"
}

# Function to show status
show_status() {
    print_info "Checking deployment status..."
    
    if [ -d "infrastructure/aws" ]; then
        cd infrastructure/aws
        
        if [ -f "terraform.tfstate" ] || terraform state list &>/dev/null; then
            print_info "Terraform state found. Showing outputs:"
            terraform output
        else
            print_warning "No Terraform state found. Infrastructure may not be deployed."
        fi
        
        cd ../..
    else
        print_error "Infrastructure directory not found. Are you in the right directory?"
    fi
}

# Function to destroy infrastructure
destroy_infrastructure() {
    print_error "WARNING: This will destroy ALL infrastructure!"
    print_error "This action cannot be undone."
    echo ""
    read -p "Type 'yes' to confirm destruction: " confirm
    
    if [ "$confirm" = "yes" ]; then
        cd infrastructure/aws
        
        print_info "Destroying infrastructure..."
        terraform destroy -auto-approve
        
        # Clean up AWS resources we created
        print_info "Cleaning up AWS resources..."
        
        # Delete S3 bucket (if empty)
        aws s3 rb "s3://${TERRAFORM_STATE_BUCKET}" --force 2>/dev/null || true
        
        # Delete DynamoDB table
        aws dynamodb delete-table --table-name "${TERRAFORM_LOCK_TABLE}" 2>/dev/null || true
        
        # Delete key pair
        aws ec2 delete-key-pair --key-name "${KEY_PAIR_NAME}" 2>/dev/null || true
        rm -f ~/.ssh/${KEY_PAIR_NAME}.pem
        
        print_success "Infrastructure destroyed successfully"
        
        cd ../..
    else
        print_info "Destruction cancelled"
    fi
}

# Parse command line arguments
PLAN_ONLY=false
DESTROY=false
STATUS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --region)
            AWS_REGION="$2"
            shift 2
            ;;
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --plan-only)
            PLAN_ONLY=true
            shift
            ;;
        --destroy)
            DESTROY=true
            shift
            ;;
        --status)
            STATUS=true
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution flow
main() {
    print_info "AWS Region: ${AWS_REGION}"
    print_info "Environment: ${ENVIRONMENT}"
    print_info "Project: ${PROJECT_NAME}"
    echo ""
    
    if [ "$STATUS" = true ]; then
        show_status
        exit 0
    fi
    
    if [ "$DESTROY" = true ]; then
        destroy_infrastructure
        exit 0
    fi
    
    # Normal deployment flow
    check_prerequisites
    setup_aws_resources
    configure_terraform
    
    if [ "$PLAN_ONLY" = true ]; then
        print_info "Plan-only mode. Creating Terraform plan..."
        cd infrastructure/aws
        terraform plan
        cd ../..
        print_info "Plan created. Use --apply to deploy."
    else
        deploy_infrastructure
        verify_deployment
        
        echo ""
        print_success "🎉 TGE Swarm deployed successfully to AWS!"
        print_info "Next steps:"
        print_info "1. Access the dashboard at the URL shown above"
        print_info "2. Configure your TGE detection parameters"
        print_info "3. Monitor performance in Grafana"
        print_info "4. Check logs in CloudWatch"
    fi
}

# Run main function
main "$@"