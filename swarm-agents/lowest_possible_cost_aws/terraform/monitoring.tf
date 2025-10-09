# Cost-Optimized Monitoring Configuration
# Basic CloudWatch with cost alerts

# CloudWatch dashboard for basic monitoring
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${local.name_prefix}-dashboard"

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
            ["AWS/EC2", "CPUUtilization", "AutoScalingGroupName", aws_autoscaling_group.main.name],
            [".", "NetworkIn", ".", "."],
            [".", "NetworkOut", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "EC2 Metrics"
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
            ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", aws_lb.main.arn_suffix],
            [".", "RequestCount", ".", "."],
            [".", "HTTPCode_Target_2XX_Count", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Load Balancer Metrics"
          period  = 300
        }
      }
    ]
  })
}

# CloudWatch alarm for high CPU usage
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "${local.name_prefix}-high-cpu"
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
    AutoScalingGroupName = aws_autoscaling_group.main.name
  }

  tags = {
    Name = "${local.name_prefix}-high-cpu-alarm"
  }
}

# CloudWatch alarm for instance status check
resource "aws_cloudwatch_metric_alarm" "instance_status_check" {
  alarm_name          = "${local.name_prefix}-instance-status-check"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "StatusCheckFailed_Instance"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Maximum"
  threshold           = "0"
  alarm_description   = "This metric monitors ec2 instance status check"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.main.name
  }

  tags = {
    Name = "${local.name_prefix}-instance-status-alarm"
  }
}

# Cost monitoring alarm
resource "aws_cloudwatch_metric_alarm" "cost_alarm" {
  alarm_name          = "${local.name_prefix}-cost-alarm"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = "86400"
  statistic           = "Maximum"
  threshold           = "150"  # Alert if monthly cost exceeds $150
  alarm_description   = "This alarm monitors AWS estimated charges"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    Currency = "USD"
  }

  tags = {
    Name = "${local.name_prefix}-cost-alarm"
  }
}

# SNS topic for alerts
resource "aws_sns_topic" "alerts" {
  name = "${local.name_prefix}-alerts"

  tags = {
    Name = "${local.name_prefix}-alerts-topic"
  }
}

# SNS topic subscription (add your email)
resource "aws_sns_topic_subscription" "email_alerts" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Lambda function for cost optimization
resource "aws_lambda_function" "cost_optimizer" {
  filename         = "${path.module}/../scripts/cost_optimizer.zip"
  function_name    = "${local.name_prefix}-cost-optimizer"
  role            = aws_iam_role.lambda_cost_optimizer.arn
  handler         = "cost_optimizer.lambda_handler"
  runtime         = "python3.9"
  timeout         = 300

  environment {
    variables = {
      ASG_NAME = aws_autoscaling_group.main.name
      REGION   = var.aws_region
    }
  }

  tags = {
    Name = "${local.name_prefix}-cost-optimizer"
  }
}

# IAM role for Lambda
resource "aws_iam_role" "lambda_cost_optimizer" {
  name_prefix = "${local.name_prefix}-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM policy for Lambda
resource "aws_iam_role_policy" "lambda_cost_optimizer" {
  name_prefix = "${local.name_prefix}-lambda"
  role        = aws_iam_role.lambda_cost_optimizer.id

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
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "autoscaling:UpdateAutoScalingGroup",
          "autoscaling:DescribeAutoScalingGroups",
          "ec2:DescribeInstances",
          "ec2:StopInstances",
          "ec2:StartInstances"
        ]
        Resource = "*"
      }
    ]
  })
}

# EventBridge rule for scheduled cost optimization
resource "aws_cloudwatch_event_rule" "cost_optimizer_schedule" {
  count = var.auto_shutdown_enabled ? 1 : 0
  
  name                = "${local.name_prefix}-cost-optimizer-schedule"
  description         = "Trigger cost optimizer Lambda"
  schedule_expression = "cron(${replace(var.auto_shutdown_schedule, " ", " ")})"

  tags = {
    Name = "${local.name_prefix}-cost-optimizer-schedule"
  }
}

# EventBridge target
resource "aws_cloudwatch_event_target" "lambda" {
  count = var.auto_shutdown_enabled ? 1 : 0
  
  rule      = aws_cloudwatch_event_rule.cost_optimizer_schedule[0].name
  target_id = "TriggerLambda"
  arn       = aws_lambda_function.cost_optimizer.arn
}

# Lambda permission for EventBridge
resource "aws_lambda_permission" "allow_eventbridge" {
  count = var.auto_shutdown_enabled ? 1 : 0
  
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cost_optimizer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.cost_optimizer_schedule[0].arn
}