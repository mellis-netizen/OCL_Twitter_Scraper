# Variables for Ultra-Low-Cost TGE Swarm Deployment

variable "aws_region" {
  description = "AWS region for deployment (us-east-1 is cheapest)"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "cost-optimized"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "tge-swarm"
}

# TGE Configuration Variables
variable "email_user" {
  description = "Email username for TGE alerts"
  type        = string
  default     = ""
  sensitive   = true
}

variable "email_password" {
  description = "Email password for TGE alerts"
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
  description = "Twitter Bearer Token for API access"
  type        = string
  default     = ""
  sensitive   = true
}

variable "key_name" {
  description = "AWS Key Pair name for EC2 access"
  type        = string
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the infrastructure"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # Restrict this in production
}

variable "spot_instance_interruption_behavior" {
  description = "Behavior when spot instance is interrupted"
  type        = string
  default     = "stop"  # stop, hibernate, or terminate
}

variable "enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring (costs extra)"
  type        = bool
  default     = false
}

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 7  # Minimal retention to save costs
}

variable "auto_shutdown_enabled" {
  description = "Enable automatic shutdown during off-hours"
  type        = bool
  default     = true
}

variable "auto_shutdown_schedule" {
  description = "Cron expression for auto shutdown (UTC)"
  type        = string
  default     = "0 22 * * *"  # 10 PM UTC daily
}

variable "auto_startup_schedule" {
  description = "Cron expression for auto startup (UTC)"
  type        = string
  default     = "0 6 * * 1-5"  # 6 AM UTC, weekdays only
}

variable "storage_size" {
  description = "EBS volume size in GB (minimal for cost)"
  type        = number
  default     = 20  # Minimum for reasonable operation
}

variable "enable_monitoring_stack" {
  description = "Enable Prometheus/Grafana monitoring"
  type        = bool
  default     = true
}

variable "enable_backup_to_s3" {
  description = "Enable S3 backups (costs extra)"
  type        = bool
  default     = false  # Local backups only by default
}

variable "domain_name" {
  description = "Domain name for SSL certificate"
  type        = string
  default     = ""
}

variable "manage_dns_with_route53" {
  description = "Whether to manage DNS with Route53"
  type        = bool
  default     = false
}

variable "alert_email" {
  description = "Email address for cost and system alerts"
  type        = string
  default     = ""
}