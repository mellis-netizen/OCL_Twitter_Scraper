# TGE Swarm IAM Roles and Policies
# Comprehensive IAM configuration following principle of least privilege

# Data source for AWS caller identity
data "aws_caller_identity" "current" {}

# IAM Role for Swarm Queen
resource "aws_iam_role" "swarm_queen" {
  name = "${local.name_prefix}-queen-role"
  
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
    Name = "${local.name_prefix}-queen-role"
    Service = "Swarm-Queen"
  }
}

# IAM Policy for Swarm Queen
resource "aws_iam_role_policy" "swarm_queen" {
  name = "${local.name_prefix}-queen-policy"
  role = aws_iam_role.swarm_queen.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/ec2/swarm-queen:*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:ListMetrics"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.redis_auth.arn,
          aws_rds_cluster.postgres.master_user_secret[0].secret_arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = [
          "${aws_s3_bucket.application_data.arn}/queen/*",
          "${aws_s3_bucket.backups.arn}/queen/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeTags"
        ]
        Resource = "*"
      }
    ]
  })
}

# IAM Instance Profile for Swarm Queen
resource "aws_iam_instance_profile" "swarm_queen" {
  name = "${local.name_prefix}-queen-profile"
  role = aws_iam_role.swarm_queen.name
}

# IAM Role for Memory Coordinator
resource "aws_iam_role" "memory_coordinator" {
  name = "${local.name_prefix}-coordinator-role"
  
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
    Name = "${local.name_prefix}-coordinator-role"
    Service = "Memory-Coordinator"
  }
}

# IAM Policy for Memory Coordinator
resource "aws_iam_role_policy" "memory_coordinator" {
  name = "${local.name_prefix}-coordinator-policy"
  role = aws_iam_role.memory_coordinator.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/ec2/memory-coordinator:*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.redis_auth.arn,
          aws_rds_cluster.postgres.master_user_secret[0].secret_arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = [
          "${aws_s3_bucket.application_data.arn}/coordinator/*",
          "${aws_s3_bucket.backups.arn}/coordinator/*"
        ]
      }
    ]
  })
}

# IAM Instance Profile for Memory Coordinator
resource "aws_iam_instance_profile" "memory_coordinator" {
  name = "${local.name_prefix}-coordinator-profile"
  role = aws_iam_role.memory_coordinator.name
}

# IAM Role for Swarm Agents
resource "aws_iam_role" "swarm_agents" {
  name = "${local.name_prefix}-agents-role"
  
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
    Name = "${local.name_prefix}-agents-role"
    Service = "Swarm-Agents"
  }
}

# IAM Policy for Swarm Agents
resource "aws_iam_role_policy" "swarm_agents" {
  name = "${local.name_prefix}-agents-policy"
  role = aws_iam_role.swarm_agents.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/ec2/swarm-agents:*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.redis_auth.arn,
          aws_rds_cluster.postgres.master_user_secret[0].secret_arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = [
          "${aws_s3_bucket.application_data.arn}/agents/*",
          "${aws_s3_bucket.backups.arn}/agents/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "autoscaling:DescribeAutoScalingGroups",
          "autoscaling:DescribeAutoScalingInstances",
          "ec2:DescribeInstances"
        ]
        Resource = "*"
      }
    ]
  })
}

# IAM Instance Profile for Swarm Agents
resource "aws_iam_instance_profile" "swarm_agents" {
  name = "${local.name_prefix}-agents-profile"
  role = aws_iam_role.swarm_agents.name
}

# IAM Role for Monitoring
resource "aws_iam_role" "monitoring" {
  name = "${local.name_prefix}-monitoring-role"
  
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
    Name = "${local.name_prefix}-monitoring-role"
    Service = "Monitoring"
  }
}

# IAM Policy for Monitoring
resource "aws_iam_role_policy" "monitoring" {
  name = "${local.name_prefix}-monitoring-policy"
  role = aws_iam_role.monitoring.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/ec2/monitoring:*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:ListMetrics",
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeTags",
          "rds:DescribeDBInstances",
          "rds:DescribeDBClusters",
          "elasticache:DescribeCacheClusters",
          "elasticache:DescribeReplicationGroups"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = [
          "${aws_s3_bucket.application_data.arn}/monitoring/*",
          "${aws_s3_bucket.backups.arn}/monitoring/*"
        ]
      }
    ]
  })
}

# IAM Instance Profile for Monitoring
resource "aws_iam_instance_profile" "monitoring" {
  name = "${local.name_prefix}-monitoring-profile"
  role = aws_iam_role.monitoring.name
}

# IAM Role for Consul
resource "aws_iam_role" "consul" {
  name = "${local.name_prefix}-consul-role"
  
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
    Name = "${local.name_prefix}-consul-role"
    Service = "Consul"
  }
}

# IAM Policy for Consul
resource "aws_iam_role_policy" "consul" {
  name = "${local.name_prefix}-consul-policy"
  role = aws_iam_role.consul.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/ec2/consul:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeTags",
          "autoscaling:DescribeAutoScalingGroups"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = [
          "${aws_s3_bucket.application_data.arn}/consul/*",
          "${aws_s3_bucket.backups.arn}/consul/*"
        ]
      }
    ]
  })
}

# IAM Instance Profile for Consul
resource "aws_iam_instance_profile" "consul" {
  name = "${local.name_prefix}-consul-profile"
  role = aws_iam_role.consul.name
}

# IAM Role for Bastion Host
resource "aws_iam_role" "bastion" {
  name = "${local.name_prefix}-bastion-role"
  
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
    Name = "${local.name_prefix}-bastion-role"
    Service = "Bastion"
  }
}

# IAM Policy for Bastion Host
resource "aws_iam_role_policy" "bastion" {
  name = "${local.name_prefix}-bastion-policy"
  role = aws_iam_role.bastion.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/ec2/bastion:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:UpdateInstanceInformation",
          "ssm:SendCommand",
          "ssm:ListCommands",
          "ssm:ListCommandInvocations",
          "ssm:DescribeInstanceInformation",
          "ssm:GetCommandInvocation"
        ]
        Resource = "*"
      }
    ]
  })
}

# IAM Instance Profile for Bastion Host
resource "aws_iam_instance_profile" "bastion" {
  name = "${local.name_prefix}-bastion-profile"
  role = aws_iam_role.bastion.name
}

# IAM Role for AWS Backup
resource "aws_iam_role" "backup" {
  name = "${local.name_prefix}-backup-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "backup.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Name = "${local.name_prefix}-backup-role"
    Service = "AWS-Backup"
  }
}

# Attach AWS managed policy for backup
resource "aws_iam_role_policy_attachment" "backup_service" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}

resource "aws_iam_role_policy_attachment" "backup_restore" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForRestores"
}

# IAM Role for CloudWatch Agent
resource "aws_iam_role" "cloudwatch_agent" {
  name = "${local.name_prefix}-cloudwatch-agent-role"
  
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
    Name = "${local.name_prefix}-cloudwatch-agent-role"
    Service = "CloudWatch-Agent"
  }
}

# Attach AWS managed policy for CloudWatch agent
resource "aws_iam_role_policy_attachment" "cloudwatch_agent" {
  role       = aws_iam_role.cloudwatch_agent.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

# IAM Instance Profile for CloudWatch Agent
resource "aws_iam_instance_profile" "cloudwatch_agent" {
  name = "${local.name_prefix}-cloudwatch-agent-profile"
  role = aws_iam_role.cloudwatch_agent.name
}

# IAM Role for ALB to write access logs to S3
resource "aws_iam_role" "alb_logs" {
  name = "${local.name_prefix}-alb-logs-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "elasticloadbalancing.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Name = "${local.name_prefix}-alb-logs-role"
    Service = "ALB-Logs"
  }
}

# S3 Bucket Policy for ALB Access Logs
data "aws_iam_policy_document" "alb_logs" {
  statement {
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::797873946194:root"] # ELB service account for us-west-2
    }
    
    actions = [
      "s3:PutObject"
    ]
    
    resources = [
      "${aws_s3_bucket.alb_logs.arn}/alb-access-logs/AWSLogs/${data.aws_caller_identity.current.account_id}/*"
    ]
  }
  
  statement {
    principals {
      type        = "Service"
      identifiers = ["delivery.logs.amazonaws.com"]
    }
    
    actions = [
      "s3:PutObject"
    ]
    
    resources = [
      "${aws_s3_bucket.alb_logs.arn}/alb-access-logs/AWSLogs/${data.aws_caller_identity.current.account_id}/*"
    ]
    
    condition {
      test     = "StringEquals"
      variable = "s3:x-amz-acl"
      values   = ["bucket-owner-full-control"]
    }
  }
  
  statement {
    principals {
      type        = "Service"
      identifiers = ["delivery.logs.amazonaws.com"]
    }
    
    actions = [
      "s3:GetBucketAcl"
    ]
    
    resources = [
      aws_s3_bucket.alb_logs.arn
    ]
  }
}

resource "aws_s3_bucket_policy" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id
  policy = data.aws_iam_policy_document.alb_logs.json
}