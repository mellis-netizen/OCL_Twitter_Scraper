# TGE Swarm AWS Infrastructure Variables
# Production deployment configuration variables

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name (production, staging, development)"
  type        = string
  default     = "production"
  
  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "Environment must be production, staging, or development."
  }
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "tge-swarm"
}

# TGE Configuration Variables
variable "email_user" {
  description = "Email username for TGE alerts (stored in Parameter Store)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "email_password" {
  description = "Email password for TGE alerts (stored in Parameter Store)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "recipient_email" {
  description = "Recipient email for TGE alerts"
  type        = string
  default     = "admin@company.com"
}

variable "twitter_bearer_token" {
  description = "Twitter Bearer Token for API access (stored in Parameter Store)"
  type        = string
  default     = ""
  sensitive   = true
}

# VPC Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]
}

variable "database_subnet_cidrs" {
  description = "CIDR blocks for database subnets"
  type        = list(string)
  default     = ["10.0.21.0/24", "10.0.22.0/24", "10.0.23.0/24"]
}

# EC2 Instance Configuration
variable "key_pair_name" {
  description = "AWS Key Pair name for EC2 instances"
  type        = string
}

variable "instance_types" {
  description = "EC2 instance types for different services"
  type = object({
    queen        = string
    coordinator  = string
    agent        = string
    database     = string
    cache        = string
    monitoring   = string
    load_balancer = string
  })
  default = {
    queen        = "t3.large"
    coordinator  = "t3.medium" 
    agent        = "t3.small"
    database     = "t3.medium"
    cache        = "t3.small"
    monitoring   = "t3.medium"
    load_balancer = "t3.small"
  }
}

# Auto Scaling Configuration
variable "swarm_agent_config" {
  description = "Configuration for swarm agent auto scaling"
  type = object({
    min_size         = number
    max_size         = number
    desired_capacity = number
    health_check_grace_period = number
    health_check_type = string
  })
  default = {
    min_size         = 2
    max_size         = 10
    desired_capacity = 5
    health_check_grace_period = 300
    health_check_type = "ELB"
  }
}

# Database Configuration
variable "postgres_config" {
  description = "PostgreSQL database configuration"
  type = object({
    engine_version    = string
    instance_class    = string
    allocated_storage = number
    max_allocated_storage = number
    backup_retention_period = number
    backup_window     = string
    maintenance_window = string
    multi_az          = bool
    deletion_protection = bool
  })
  default = {
    engine_version    = "15.4"
    instance_class    = "db.t3.medium"
    allocated_storage = 100
    max_allocated_storage = 1000
    backup_retention_period = 7
    backup_window     = "03:00-04:00"
    maintenance_window = "sun:04:00-sun:05:00"
    multi_az          = true
    deletion_protection = true
  }
}

# Redis Configuration
variable "redis_config" {
  description = "Redis cluster configuration"
  type = object({
    node_type                = string
    num_cache_clusters       = number
    parameter_group_name     = string
    port                     = number
    engine_version           = string
    automatic_failover_enabled = bool
    multi_az_enabled         = bool
    at_rest_encryption_enabled = bool
    transit_encryption_enabled = bool
  })
  default = {
    node_type                = "cache.t3.micro"
    num_cache_clusters       = 3
    parameter_group_name     = "default.redis7.cluster.on"
    port                     = 6379
    engine_version           = "7.0"
    automatic_failover_enabled = true
    multi_az_enabled         = true
    at_rest_encryption_enabled = true
    transit_encryption_enabled = true
  }
}

# Load Balancer Configuration
variable "alb_config" {
  description = "Application Load Balancer configuration"
  type = object({
    enable_deletion_protection = bool
    idle_timeout              = number
    enable_http2              = bool
    enable_cross_zone_load_balancing = bool
  })
  default = {
    enable_deletion_protection = true
    idle_timeout              = 60
    enable_http2              = true
    enable_cross_zone_load_balancing = true
  }
}

# Monitoring Configuration
variable "cloudwatch_config" {
  description = "CloudWatch monitoring configuration"
  type = object({
    log_retention_days    = number
    detailed_monitoring   = bool
    enable_insights       = bool
    dashboard_enabled     = bool
  })
  default = {
    log_retention_days    = 30
    detailed_monitoring   = true
    enable_insights       = true
    dashboard_enabled     = true
  }
}

# Security Configuration
variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the infrastructure"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # Restrict this in production
}

variable "enable_flow_logs" {
  description = "Enable VPC flow logs"
  type        = bool
  default     = true
}

variable "enable_cloudtrail" {
  description = "Enable CloudTrail logging"
  type        = bool
  default     = true
}

# Backup Configuration
variable "backup_config" {
  description = "Backup and disaster recovery configuration"
  type = object({
    backup_vault_name = string
    backup_schedule   = string
    retention_days    = number
    copy_to_destination = bool
    destination_region = string
  })
  default = {
    backup_vault_name = "tge-swarm-backup-vault"
    backup_schedule   = "cron(0 2 * * ? *)"  # Daily at 2 AM
    retention_days    = 30
    copy_to_destination = true
    destination_region = "us-east-1"
  }
}

# Cost Optimization
variable "enable_spot_instances" {
  description = "Enable spot instances for cost optimization (non-critical workloads)"
  type        = bool
  default     = false
}

variable "spot_instance_types" {
  description = "Instance types to use for spot instances"
  type        = list(string)
  default     = ["t3.small", "t3.medium", "m5.large"]
}

# Domain and SSL Configuration
variable "domain_name" {
  description = "Domain name for the TGE Swarm application"
  type        = string
  default     = ""
}

variable "hosted_zone_id" {
  description = "Route53 hosted zone ID for domain management"
  type        = string
  default     = ""
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS"
  type        = string
  default     = ""
}

# Tagging
variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# Feature Flags
variable "enable_multi_region" {
  description = "Enable multi-region deployment for disaster recovery"
  type        = bool
  default     = false
}

variable "enable_container_insights" {
  description = "Enable ECS Container Insights"
  type        = bool
  default     = true
}

variable "enable_prometheus_monitoring" {
  description = "Enable managed Prometheus monitoring"
  type        = bool
  default     = true
}