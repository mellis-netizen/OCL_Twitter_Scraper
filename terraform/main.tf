# Terraform configuration for Crypto TGE Monitor on AWS EC2
# Alternative to CloudFormation for infrastructure as code

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.small"
}

variable "key_pair_name" {
  description = "EC2 Key Pair name"
  type        = string
}

variable "email_address" {
  description = "Email address for notifications"
  type        = string
}

variable "repository_url" {
  description = "Git repository URL"
  type        = string
  default     = ""
}

variable "s3_bucket_name" {
  description = "S3 bucket name (leave empty to create new)"
  type        = string
  default     = ""
}

variable "enable_s3_backup" {
  description = "Enable S3 backup functionality"
  type        = bool
  default     = true
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
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
}

# Local values
locals {
  s3_bucket_name = var.enable_s3_backup ? (var.s3_bucket_name != "" ? var.s3_bucket_name : "crypto-tge-monitor-${random_id.bucket_suffix.hex}") : ""
  
  common_tags = {
    Environment = var.environment
    Application = "crypto-tge-monitor"
    Project     = "TGE-Monitor"
    ManagedBy   = "Terraform"
  }
}

# Random ID for unique resource names
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# VPC and Networking
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(local.common_tags, {
    Name = "crypto-tge-monitor-vpc"
  })
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.common_tags, {
    Name = "crypto-tge-monitor-igw"
  })
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "crypto-tge-monitor-public-subnet"
  })
}

resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]

  tags = merge(local.common_tags, {
    Name = "crypto-tge-monitor-private-subnet"
  })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(local.common_tags, {
    Name = "crypto-tge-monitor-public-rt"
  })
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# Security Group
resource "aws_security_group" "app" {
  name_prefix = "crypto-tge-monitor-"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP Health Check"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS Health Check"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "crypto-tge-monitor-sg"
  })
}

# S3 Bucket (optional)
resource "aws_s3_bucket" "backup" {
  count  = var.enable_s3_backup && var.s3_bucket_name == "" ? 1 : 0
  bucket = local.s3_bucket_name

  tags = local.common_tags
}

resource "aws_s3_bucket_encryption_configuration" "backup" {
  count  = var.enable_s3_backup && var.s3_bucket_name == "" ? 1 : 0
  bucket = aws_s3_bucket.backup[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "backup" {
  count  = var.enable_s3_backup && var.s3_bucket_name == "" ? 1 : 0
  bucket = aws_s3_bucket.backup[0].id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "backup" {
  count  = var.enable_s3_backup && var.s3_bucket_name == "" ? 1 : 0
  bucket = aws_s3_bucket.backup[0].id

  rule {
    id     = "delete_old_backups"
    status = "Enabled"

    expiration {
      days = 90
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "backup" {
  count  = var.enable_s3_backup && var.s3_bucket_name == "" ? 1 : 0
  bucket = aws_s3_bucket.backup[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# SNS Topic
resource "aws_sns_topic" "alerts" {
  name = "crypto-tge-monitor-alerts"

  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.email_address
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "app" {
  name              = "/aws/ec2/crypto-tge-monitor"
  retention_in_days = 30

  tags = local.common_tags
}

# IAM Role and Policy
resource "aws_iam_role" "ec2" {
  name = "crypto-tge-monitor-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# IAM Policy Document
data "aws_iam_policy_document" "ec2" {
  # CloudWatch and basic EC2 permissions
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogStreams",
      "logs:DescribeLogGroups"
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "cloudwatch:PutMetricData"
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "ec2:DescribeInstances",
      "ec2:DescribeInstanceStatus"
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "sns:Publish"
    ]
    resources = [aws_sns_topic.alerts.arn]
  }

  # S3 permissions only if S3 backup is enabled
  dynamic "statement" {
    for_each = var.enable_s3_backup ? [1] : []
    content {
      effect = "Allow"
      actions = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ]
      resources = [
        var.s3_bucket_name == "" && var.enable_s3_backup ? "${aws_s3_bucket.backup[0].arn}/*" : "arn:aws:s3:::${var.s3_bucket_name}/*"
      ]
    }
  }

  dynamic "statement" {
    for_each = var.enable_s3_backup ? [1] : []
    content {
      effect = "Allow"
      actions = [
        "s3:ListBucket"
      ]
      resources = [
        var.s3_bucket_name == "" && var.enable_s3_backup ? aws_s3_bucket.backup[0].arn : "arn:aws:s3:::${var.s3_bucket_name}"
      ]
    }
  }
}

resource "aws_iam_role_policy" "ec2" {
  name = "crypto-tge-monitor-policy"
  role = aws_iam_role.ec2.id
  policy = data.aws_iam_policy_document.ec2.json
}

resource "aws_iam_role_policy_attachment" "cloudwatch" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_instance_profile" "ec2" {
  name = "crypto-tge-monitor-profile"
  role = aws_iam_role.ec2.name
}

# User Data Script
locals {
  user_data = base64encode(templatefile("${path.module}/../ec2-user-data.sh", {
    repo_url         = var.repository_url
    sns_topic_arn    = aws_sns_topic.alerts.arn
    s3_backup_bucket = local.s3_bucket_name
  }))
}

# Launch Template
resource "aws_launch_template" "app" {
  name_prefix   = "crypto-tge-monitor-"
  image_id      = data.aws_ami.amazon_linux.id
  instance_type = var.instance_type
  key_name      = var.key_pair_name

  vpc_security_group_ids = [aws_security_group.app.id]

  iam_instance_profile {
    name = aws_iam_instance_profile.ec2.name
  }

  user_data = local.user_data

  tag_specifications {
    resource_type = "instance"
    tags = merge(local.common_tags, {
      Name = "crypto-tge-monitor"
    })
  }

  tags = local.common_tags
}

# Auto Scaling Group
resource "aws_autoscaling_group" "app" {
  name                = "crypto-tge-monitor-asg"
  vpc_zone_identifier = [aws_subnet.public.id]
  min_size            = 1
  max_size            = 1
  desired_capacity    = 1

  launch_template {
    id      = aws_launch_template.app.id
    version = "$Latest"
  }

  health_check_type         = "EC2"
  health_check_grace_period = 300

  tag {
    key                 = "Name"
    value               = "crypto-tge-monitor-asg"
    propagate_at_launch = false
  }

  dynamic "tag" {
    for_each = local.common_tags
    content {
      key                 = tag.key
      value               = tag.value
      propagate_at_launch = false
    }
  }
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "crypto-tge-monitor-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ec2 cpu utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.app.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "status_check" {
  alarm_name          = "crypto-tge-monitor-status-check"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Maximum"
  threshold           = "0"
  alarm_description   = "This metric monitors ec2 status check"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.app.name
  }

  tags = local.common_tags
}

# Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnet_id" {
  description = "Public Subnet ID"
  value       = aws_subnet.public.id
}

output "security_group_id" {
  description = "Security Group ID"
  value       = aws_security_group.app.id
}

output "s3_bucket_name" {
  description = "S3 Bucket Name (if enabled)"
  value       = var.enable_s3_backup ? local.s3_bucket_name : "S3 backup disabled"
}

output "sns_topic_arn" {
  description = "SNS Topic ARN"
  value       = aws_sns_topic.alerts.arn
}

output "autoscaling_group_name" {
  description = "Auto Scaling Group Name"
  value       = aws_autoscaling_group.app.name
}

output "log_group_name" {
  description = "CloudWatch Log Group Name"
  value       = aws_cloudwatch_log_group.app.name
}