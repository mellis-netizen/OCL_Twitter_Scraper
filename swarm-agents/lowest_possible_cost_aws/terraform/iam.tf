# IAM Configuration for Ultra-Low-Cost Deployment
# Minimal permissions for cost optimization features

# IAM role for main instance
resource "aws_iam_role" "main" {
  name_prefix = "${local.name_prefix}-main"

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

  tags = {
    Name = "${local.name_prefix}-main-role"
  }
}

# Policy for main instance (cost optimization features)
resource "aws_iam_role_policy" "main" {
  name_prefix = "${local.name_prefix}-main"
  role        = aws_iam_role.main.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # CloudWatch for basic monitoring
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:ListMetrics"
        ]
        Resource = "*"
      },
      # EC2 for auto-shutdown/startup
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:StopInstances",
          "ec2:StartInstances",
          "ec2:DescribeInstanceStatus"
        ]
        Resource = "*"
      },
      # S3 for backups (if enabled)
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${local.name_prefix}-backups",
          "arn:aws:s3:::${local.name_prefix}-backups/*"
        ]
      },
      # Systems Manager for patch management
      {
        Effect = "Allow"
        Action = [
          "ssm:UpdateInstanceInformation",
          "ssm:SendCommand",
          "ssm:GetCommandInvocation"
        ]
        Resource = "*"
      },
      # Cost monitoring
      {
        Effect = "Allow"
        Action = [
          "ce:GetCostAndUsage",
          "ce:GetDimensionValues",
          "ce:GetReservationCoverage",
          "ce:GetReservationPurchaseRecommendation",
          "ce:GetUsageReport"
        ]
        Resource = "*"
      }
    ]
  })
}

# Instance profile for main instance
resource "aws_iam_instance_profile" "main" {
  name_prefix = "${local.name_prefix}-main"
  role        = aws_iam_role.main.name

  tags = {
    Name = "${local.name_prefix}-main-profile"
  }
}

# IAM role for backup instance (minimal permissions)
resource "aws_iam_role" "backup" {
  name_prefix = "${local.name_prefix}-backup"

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

  tags = {
    Name = "${local.name_prefix}-backup-role"
  }
}

# Minimal policy for backup instance
resource "aws_iam_role_policy" "backup" {
  name_prefix = "${local.name_prefix}-backup"
  role        = aws_iam_role.backup.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Basic CloudWatch
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      },
      # EC2 describe for health checks
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeInstanceStatus"
        ]
        Resource = "*"
      }
    ]
  })
}

# Instance profile for backup instance
resource "aws_iam_instance_profile" "backup" {
  name_prefix = "${local.name_prefix}-backup"
  role        = aws_iam_role.backup.name

  tags = {
    Name = "${local.name_prefix}-backup-profile"
  }
}

# Service-linked role for Auto Scaling (if not exists)
resource "aws_iam_service_linked_role" "autoscaling" {
  aws_service_name = "autoscaling.amazonaws.com"
  description      = "Service-linked role for Auto Scaling"
  
  lifecycle {
    ignore_changes = [aws_service_name]
  }
}