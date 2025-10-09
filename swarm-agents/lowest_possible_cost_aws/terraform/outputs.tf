# Outputs for Ultra-Low-Cost TGE Swarm Deployment

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_id" {
  description = "ID of the public subnet"
  value       = aws_subnet.public.id
}

output "load_balancer_dns" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "load_balancer_zone_id" {
  description = "Zone ID of the load balancer"
  value       = aws_lb.main.zone_id
}

output "main_instance_security_group_id" {
  description = "Security group ID for main instance"
  value       = aws_security_group.main.id
}

output "backup_instance_id" {
  description = "Instance ID of backup instance"
  value       = aws_instance.backup.id
}

output "backup_instance_private_ip" {
  description = "Private IP of backup instance"
  value       = aws_instance.backup.private_ip
}

output "autoscaling_group_name" {
  description = "Name of the Auto Scaling Group"
  value       = aws_autoscaling_group.main.name
}

output "sns_topic_arn" {
  description = "ARN of SNS topic for alerts"
  value       = aws_sns_topic.alerts.arn
}

output "s3_backup_bucket" {
  description = "S3 bucket for backups (if enabled)"
  value       = var.enable_backup_to_s3 ? aws_s3_bucket.backups[0].bucket : "disabled"
}

output "ssl_certificate_arn" {
  description = "ARN of SSL certificate"
  value       = var.domain_name != "" ? aws_acm_certificate.main[0].arn : "not_configured"
}

output "cost_optimizer_lambda_function_name" {
  description = "Name of cost optimizer Lambda function"
  value       = aws_lambda_function.cost_optimizer.function_name
}

output "cloudwatch_dashboard_url" {
  description = "URL to CloudWatch dashboard"
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}

# Cost estimation outputs
output "estimated_monthly_cost" {
  description = "Estimated monthly cost breakdown"
  value = {
    # Spot instance costs (assuming 70% savings)
    main_instance_spot = "~$4.50/month (t3.small spot)"
    backup_instance    = "~$3.80/month (t3.nano on-demand)"
    
    # Storage costs
    ebs_storage = "~$2.00/month (20GB gp3)"
    
    # Load balancer costs
    application_lb = "~$16.20/month"
    
    # Data transfer (estimated)
    data_transfer = "~$5.00/month (assuming moderate usage)"
    
    # SSL certificate
    ssl_cert = "$0.00/month (ACM is free)"
    
    # Monitoring
    cloudwatch = "~$3.50/month (basic metrics)"
    
    # SNS
    sns_notifications = "~$0.50/month"
    
    # Lambda
    cost_optimizer_lambda = "~$0.20/month"
    
    # S3 (if enabled)
    s3_backups = var.enable_backup_to_s3 ? "~$1.00/month" : "$0.00/month (disabled)"
    
    # Estimated total
    total_estimated = "~$35-45/month (excluding data transfer overages)"
  }
}

# Access information
output "access_information" {
  description = "How to access the deployed services"
  value = {
    load_balancer_url = "https://${aws_lb.main.dns_name}"
    tge_swarm_api    = "https://${aws_lb.main.dns_name}/api"
    grafana_dashboard = var.enable_monitoring_stack ? "https://${aws_lb.main.dns_name}/grafana" : "disabled"
    ssh_to_backup    = "ssh -i <your-key>.pem ec2-user@${aws_instance.backup.public_ip}"
  }
}

# Important notes
output "cost_optimization_notes" {
  description = "Important notes about cost optimization"
  value = {
    spot_instances = "Main instance uses spot pricing - may be interrupted"
    single_az = "Deployed in single AZ to minimize costs"
    auto_shutdown = var.auto_shutdown_enabled ? "Auto-shutdown enabled: ${var.auto_shutdown_schedule}" : "Auto-shutdown disabled"
    monitoring = "Basic monitoring only - detailed monitoring disabled to save costs"
    backups = var.enable_backup_to_s3 ? "S3 backups enabled with lifecycle policies" : "Local backups only"
    scaling = "Minimal scaling configuration - manual intervention may be needed for high load"
  }
}