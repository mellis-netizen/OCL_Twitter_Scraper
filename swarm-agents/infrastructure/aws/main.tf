# TGE Swarm AWS Infrastructure
# Production-ready EC2 deployment with high availability, security, and monitoring
# AWS EC2 Deployment Engineer: Claude

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    # Configure with your S3 bucket for state storage
    # bucket = "tge-swarm-terraform-state"
    # key    = "production/terraform.tfstate"
    # region = "us-west-2"
    # encrypt = true
    # dynamodb_table = "tge-swarm-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "TGE-Swarm"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = "TGE-Swarm-Team"
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

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

# Local values for computed configurations
locals {
  name_prefix = "${var.project_name}-${var.environment}"
  
  availability_zones = slice(data.aws_availability_zones.available.names, 0, 3)
  
  # Instance sizing recommendations based on current docker-compose configuration
  instance_types = {
    queen        = "t3.large"    # 2 vCPU, 8GB RAM for Queen Orchestrator
    coordinator  = "t3.medium"   # 2 vCPU, 4GB RAM for Memory Coordinator  
    agent        = "t3.small"    # 2 vCPU, 2GB RAM for Agents
    database     = "t3.medium"   # 2 vCPU, 4GB RAM for PostgreSQL
    cache        = "t3.small"    # 2 vCPU, 2GB RAM for Redis
    monitoring   = "t3.medium"   # 2 vCPU, 4GB RAM for Prometheus/Grafana
    load_balancer = "t3.small"   # 2 vCPU, 2GB RAM for HAProxy
  }
  
  # Common ports used by the swarm services
  service_ports = {
    queen_api     = 8080
    queen_metrics = 8001
    coordinator   = 8002
    postgres      = 5432
    redis_start   = 7001
    redis_end     = 7003
    prometheus    = 9090
    grafana       = 3000
    haproxy_http  = 80
    haproxy_https = 443
    haproxy_stats = 8404
    consul        = 8500
    jaeger        = 16686
    alertmanager  = 9093
  }
}