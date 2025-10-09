# TGE Swarm Ultra-Low-Cost AWS Infrastructure
# Cost Optimization Engineer: Claude
# Target: Under $100-150/month with full functionality

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    # Use existing bucket or create a small one
    # bucket = "tge-swarm-cost-optimized-state"
    # key    = "cost-optimized/terraform.tfstate"
    # region = "us-east-1"  # Cheapest region
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project         = "TGE-Swarm-CostOptimized"
      Environment     = var.environment
      ManagedBy       = "Terraform"
      CostOptimized   = "true"
      Owner           = "TGE-Swarm-Team"
    }
  }
}

# Use cheapest region (us-east-1)
data "aws_availability_zones" "available" {
  state = "available"
  filter {
    name   = "opt-in-status"
    values = ["opt-in-not-required"]
  }
}

# Get latest Amazon Linux 2 AMI (free tier eligible)
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
  
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Local values for ultra-cost optimization
locals {
  name_prefix = "${var.project_name}-${var.environment}-cost"
  
  # Use only one AZ to minimize costs
  availability_zone = data.aws_availability_zones.available.names[0]
  
  # Ultra-small instance types for maximum cost savings
  instance_types = {
    # Single consolidated instance running all services
    all_in_one = "t3.small"    # 2 vCPU, 2GB RAM - runs everything
    # Backup instance for critical failover
    backup     = "t3.nano"     # 2 vCPU, 0.5GB RAM - minimal backup
  }
  
  # Spot instance configuration for 60-90% cost savings
  spot_price = "0.0052"  # Max price for t3.small (current on-demand is ~$0.0208)
  
  # Essential ports only
  service_ports = {
    ssh           = 22
    http          = 80
    https         = 443
    queen_api     = 8080
    grafana       = 3000
    prometheus    = 9090
  }
}