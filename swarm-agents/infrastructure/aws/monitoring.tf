# TGE Swarm CloudWatch Monitoring Configuration
# Comprehensive monitoring, alerting, and logging for the swarm infrastructure

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "swarm_queen" {
  name              = "/aws/ec2/swarm-queen"
  retention_in_days = var.cloudwatch_config.log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn
  
  tags = {
    Name = "${local.name_prefix}-queen-logs"
    Environment = var.environment
    Service = "Swarm-Queen"
  }
}

resource "aws_cloudwatch_log_group" "memory_coordinator" {
  name              = "/aws/ec2/memory-coordinator"
  retention_in_days = var.cloudwatch_config.log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn
  
  tags = {
    Name = "${local.name_prefix}-coordinator-logs"
    Environment = var.environment
    Service = "Memory-Coordinator"
  }
}

resource "aws_cloudwatch_log_group" "swarm_agents" {
  name              = "/aws/ec2/swarm-agents"
  retention_in_days = var.cloudwatch_config.log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn
  
  tags = {
    Name = "${local.name_prefix}-agents-logs"
    Environment = var.environment
    Service = "Swarm-Agents"
  }
}

resource "aws_cloudwatch_log_group" "monitoring" {
  name              = "/aws/ec2/monitoring"
  retention_in_days = var.cloudwatch_config.log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn
  
  tags = {
    Name = "${local.name_prefix}-monitoring-logs"
    Environment = var.environment
    Service = "Monitoring"
  }
}

resource "aws_cloudwatch_log_group" "consul" {
  name              = "/aws/ec2/consul"
  retention_in_days = var.cloudwatch_config.log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn
  
  tags = {
    Name = "${local.name_prefix}-consul-logs"
    Environment = var.environment
    Service = "Consul"
  }
}

resource "aws_cloudwatch_log_group" "bastion" {
  name              = "/aws/ec2/bastion"
  retention_in_days = var.cloudwatch_config.log_retention_days
  kms_key_id        = aws_kms_key.cloudwatch.arn
  
  tags = {
    Name = "${local.name_prefix}-bastion-logs"
    Environment = var.environment
    Service = "Bastion"
  }
}

# KMS Key for CloudWatch Logs encryption
resource "aws_kms_key" "cloudwatch" {
  description             = "KMS key for CloudWatch logs encryption"
  deletion_window_in_days = 7
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Effect = "Allow"
        Principal = {
          Service = "logs.${var.aws_region}.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })
  
  tags = {
    Name = "${local.name_prefix}-cloudwatch-kms"
    Environment = var.environment
  }
}

resource "aws_kms_alias" "cloudwatch" {
  name          = "alias/${local.name_prefix}-cloudwatch"
  target_key_id = aws_kms_key.cloudwatch.key_id
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  count = var.cloudwatch_config.dashboard_enabled ? 1 : 0
  
  dashboard_name = "${local.name_prefix}-swarm-dashboard"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        
        properties = {
          metrics = [
            ["AWS/EC2", "CPUUtilization", "InstanceId", aws_instance.swarm_queen.id],
            ["AWS/EC2", "CPUUtilization", "InstanceId", aws_instance.memory_coordinator.id],
            ["AWS/EC2", "CPUUtilization", "InstanceId", aws_instance.monitoring.id]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "EC2 CPU Utilization"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        
        properties = {
          metrics = [
            ["AWS/EC2", "MemoryUtilization", "InstanceId", aws_instance.swarm_queen.id],
            ["AWS/EC2", "MemoryUtilization", "InstanceId", aws_instance.memory_coordinator.id],
            ["AWS/EC2", "MemoryUtilization", "InstanceId", aws_instance.monitoring.id]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "EC2 Memory Utilization"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        
        properties = {
          metrics = [
            ["AWS/RDS", "CPUUtilization", "DBClusterIdentifier", aws_rds_cluster.postgres.cluster_identifier],
            ["AWS/RDS", "DatabaseConnections", "DBClusterIdentifier", aws_rds_cluster.postgres.cluster_identifier]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "RDS Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        
        properties = {
          metrics = [
            ["AWS/ElastiCache", "CPUUtilization", "ReplicationGroupId", aws_elasticache_replication_group.redis.replication_group_id],
            ["AWS/ElastiCache", "CurrConnections", "ReplicationGroupId", aws_elasticache_replication_group.redis.replication_group_id]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "ElastiCache Metrics"
          period  = 300
        }
      },
      {
        type   = "log"
        x      = 0
        y      = 12
        width  = 24
        height = 6
        
        properties = {
          query   = "SOURCE '/aws/ec2/swarm-queen' | fields @timestamp, @message | sort @timestamp desc | limit 100"
          region  = var.aws_region
          title   = "Recent Swarm Queen Logs"
        }
      }
    ]
  })
}

# CloudWatch Alarms for EC2 Instances
resource "aws_cloudwatch_metric_alarm" "queen_cpu_high" {
  alarm_name          = "${local.name_prefix}-queen-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors Queen CPU utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    InstanceId = aws_instance.swarm_queen.id
  }
  
  tags = {
    Name = "${local.name_prefix}-queen-cpu-alarm"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_metric_alarm" "queen_memory_high" {
  alarm_name          = "${local.name_prefix}-queen-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MemoryUtilization"
  namespace           = "CWAgent"
  period              = "300"
  statistic           = "Average"
  threshold           = "85"
  alarm_description   = "This metric monitors Queen memory utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    InstanceId = aws_instance.swarm_queen.id
  }
  
  tags = {
    Name = "${local.name_prefix}-queen-memory-alarm"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_metric_alarm" "queen_disk_space" {
  alarm_name          = "${local.name_prefix}-queen-disk-space"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "disk_free"
  namespace           = "CWAgent"
  period              = "300"
  statistic           = "Average"
  threshold           = "20"  # Less than 20% free space
  alarm_description   = "This metric monitors Queen disk space"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    InstanceId = aws_instance.swarm_queen.id
    device     = "/dev/xvdf"
    fstype     = "ext4"
    path       = "/app/data"
  }
  
  tags = {
    Name = "${local.name_prefix}-queen-disk-alarm"
    Environment = var.environment
  }
}

# Load Balancer Health Alarms
resource "aws_cloudwatch_metric_alarm" "alb_target_response_time" {
  alarm_name          = "${local.name_prefix}-alb-response-time"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = "300"
  statistic           = "Average"
  threshold           = "5"  # 5 seconds
  alarm_description   = "ALB target response time is too high"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }
  
  tags = {
    Name = "${local.name_prefix}-alb-response-time-alarm"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_metric_alarm" "alb_unhealthy_targets" {
  alarm_name          = "${local.name_prefix}-alb-unhealthy-targets"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "UnHealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = "300"
  statistic           = "Average"
  threshold           = "0"
  alarm_description   = "ALB has unhealthy targets"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    TargetGroup  = aws_lb_target_group.queen.arn_suffix
    LoadBalancer = aws_lb.main.arn_suffix
  }
  
  tags = {
    Name = "${local.name_prefix}-alb-unhealthy-targets-alarm"
    Environment = var.environment
  }
}

# Auto Scaling Group Alarms
resource "aws_cloudwatch_metric_alarm" "asg_instances_low" {
  alarm_name          = "${local.name_prefix}-asg-instances-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "GroupInServiceInstances"
  namespace           = "AWS/AutoScaling"
  period              = "300"
  statistic           = "Average"
  threshold           = var.swarm_agent_config.min_size
  alarm_description   = "Auto Scaling Group has too few instances"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.swarm_agents.name
  }
  
  tags = {
    Name = "${local.name_prefix}-asg-instances-low-alarm"
    Environment = var.environment
  }
}

# Custom Metrics for TGE Application
resource "aws_cloudwatch_log_metric_filter" "tge_detections" {
  name           = "${local.name_prefix}-tge-detections"
  log_group_name = aws_cloudwatch_log_group.swarm_queen.name
  pattern        = "[timestamp, level=\"INFO\", message=\"TGE_DETECTION\", ...]"
  
  metric_transformation {
    name      = "TGEDetections"
    namespace = "TGE/Swarm"
    value     = "1"
  }
}

resource "aws_cloudwatch_log_metric_filter" "api_errors" {
  name           = "${local.name_prefix}-api-errors"
  log_group_name = aws_cloudwatch_log_group.swarm_queen.name
  pattern        = "[timestamp, level=\"ERROR\", ...]"
  
  metric_transformation {
    name      = "APIErrors"
    namespace = "TGE/Swarm"
    value     = "1"
  }
}

# Custom Alarm for TGE Detection Rate
resource "aws_cloudwatch_metric_alarm" "tge_detection_rate_low" {
  alarm_name          = "${local.name_prefix}-tge-detection-rate-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "TGEDetections"
  namespace           = "TGE/Swarm"
  period              = "3600"  # 1 hour
  statistic           = "Sum"
  threshold           = "5"  # Less than 5 detections per hour
  alarm_description   = "TGE detection rate is too low"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "breaching"
  
  tags = {
    Name = "${local.name_prefix}-tge-detection-rate-alarm"
    Environment = var.environment
  }
}

# CloudWatch Insights Queries (if enabled)
resource "aws_cloudwatch_query_definition" "error_analysis" {
  count = var.cloudwatch_config.enable_insights ? 1 : 0
  
  name = "${local.name_prefix}-error-analysis"
  
  log_group_names = [
    aws_cloudwatch_log_group.swarm_queen.name,
    aws_cloudwatch_log_group.memory_coordinator.name,
    aws_cloudwatch_log_group.swarm_agents.name
  ]
  
  query_string = <<EOF
fields @timestamp, @message, @logStream
| filter @message like /ERROR/
| stats count() by @logStream
| sort count desc
EOF
}

resource "aws_cloudwatch_query_definition" "performance_analysis" {
  count = var.cloudwatch_config.enable_insights ? 1 : 0
  
  name = "${local.name_prefix}-performance-analysis"
  
  log_group_names = [
    aws_cloudwatch_log_group.swarm_queen.name
  ]
  
  query_string = <<EOF
fields @timestamp, @message
| filter @message like /PERFORMANCE/
| parse @message /response_time=(?<response_time>\d+)/
| stats avg(response_time), max(response_time), min(response_time) by bin(5m)
EOF
}

# SNS Topic for Alerts (enhanced)
resource "aws_sns_topic_subscription" "email_alerts" {
  count = var.environment == "production" ? 1 : 0
  
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = "alerts@tge-swarm.com"  # Replace with actual email
}

# CloudWatch Events Rule for Instance State Changes
resource "aws_cloudwatch_event_rule" "instance_state_change" {
  name        = "${local.name_prefix}-instance-state-change"
  description = "Capture EC2 instance state changes"
  
  event_pattern = jsonencode({
    source      = ["aws.ec2"]
    detail-type = ["EC2 Instance State-change Notification"]
    detail = {
      state = ["terminated", "stopping", "stopped"]
    }
  })
}

resource "aws_cloudwatch_event_target" "sns" {
  rule      = aws_cloudwatch_event_rule.instance_state_change.name
  target_id = "SendToSNS"
  arn       = aws_sns_topic.alerts.arn
}

# CloudWatch Agent Configuration
resource "aws_ssm_parameter" "cloudwatch_agent_config" {
  name  = "/cloudwatch-agent/config"
  type  = "String"
  value = jsonencode({
    agent = {
      metrics_collection_interval = 60
      run_as_user                 = "cwagent"
    }
    metrics = {
      namespace = "CWAgent"
      metrics_collected = {
        cpu = {
          measurement = [
            "cpu_usage_idle",
            "cpu_usage_iowait",
            "cpu_usage_user",
            "cpu_usage_system"
          ]
          metrics_collection_interval = 60
          totalcpu                    = false
        }
        disk = {
          measurement = [
            "used_percent"
          ]
          metrics_collection_interval = 60
          resources = [
            "*"
          ]
        }
        diskio = {
          measurement = [
            "io_time"
          ]
          metrics_collection_interval = 60
          resources = [
            "*"
          ]
        }
        mem = {
          measurement = [
            "mem_used_percent"
          ]
          metrics_collection_interval = 60
        }
        netstat = {
          measurement = [
            "tcp_established",
            "tcp_time_wait"
          ]
          metrics_collection_interval = 60
        }
        swap = {
          measurement = [
            "swap_used_percent"
          ]
          metrics_collection_interval = 60
        }
      }
    }
    logs = {
      logs_collected = {
        files = {
          collect_list = [
            {
              file_path      = "/var/log/messages"
              log_group_name = "/aws/ec2/system"
              log_stream_name = "{instance_id}/messages"
            },
            {
              file_path      = "/opt/tge-swarm/logs/*.log"
              log_group_name = "/aws/ec2/application"
              log_stream_name = "{instance_id}/application"
            }
          ]
        }
      }
    }
  })
  
  tags = {
    Name = "${local.name_prefix}-cloudwatch-agent-config"
    Environment = var.environment
  }
}