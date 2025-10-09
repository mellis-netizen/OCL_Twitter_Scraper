# TGE Swarm Infrastructure Outputs
# Important endpoints, credentials, and configuration details

# VPC and Networking
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "database_subnet_ids" {
  description = "IDs of the database subnets"
  value       = aws_subnet.database[*].id
}

# Load Balancer
output "load_balancer_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "load_balancer_zone_id" {
  description = "Zone ID of the Application Load Balancer"
  value       = aws_lb.main.zone_id
}

output "load_balancer_arn" {
  description = "ARN of the Application Load Balancer"
  value       = aws_lb.main.arn
}

output "internal_load_balancer_dns_name" {
  description = "DNS name of the internal Network Load Balancer"
  value       = aws_lb.internal.dns_name
}

# Application URLs
output "swarm_queen_url" {
  description = "URL to access the Swarm Queen API"
  value       = var.certificate_arn != "" ? "https://${aws_lb.main.dns_name}" : "http://${aws_lb.main.dns_name}"
}

output "grafana_url" {
  description = "URL to access Grafana dashboard"
  value       = var.certificate_arn != "" ? "https://${aws_lb.main.dns_name}/grafana" : "http://${aws_lb.main.dns_name}/grafana"
}

output "prometheus_url" {
  description = "URL to access Prometheus"
  value       = var.certificate_arn != "" ? "https://${aws_lb.main.dns_name}/prometheus" : "http://${aws_lb.main.dns_name}/prometheus"
}

# EC2 Instances
output "swarm_queen_instance_id" {
  description = "Instance ID of the Swarm Queen"
  value       = aws_instance.swarm_queen.id
}

output "swarm_queen_private_ip" {
  description = "Private IP of the Swarm Queen"
  value       = aws_instance.swarm_queen.private_ip
}

output "memory_coordinator_instance_id" {
  description = "Instance ID of the Memory Coordinator"
  value       = aws_instance.memory_coordinator.id
}

output "memory_coordinator_private_ip" {
  description = "Private IP of the Memory Coordinator"
  value       = aws_instance.memory_coordinator.private_ip
}

output "monitoring_instance_id" {
  description = "Instance ID of the Monitoring server"
  value       = aws_instance.monitoring.id
}

output "monitoring_private_ip" {
  description = "Private IP of the Monitoring server"
  value       = aws_instance.monitoring.private_ip
}

output "consul_instance_id" {
  description = "Instance ID of the Consul server"
  value       = aws_instance.consul.id
}

output "consul_private_ip" {
  description = "Private IP of the Consul server"
  value       = aws_instance.consul.private_ip
}

output "bastion_instance_id" {
  description = "Instance ID of the Bastion host"
  value       = aws_instance.bastion.id
}

output "bastion_public_ip" {
  description = "Public IP of the Bastion host"
  value       = aws_instance.bastion.public_ip
}

# Auto Scaling Group
output "swarm_agents_asg_name" {
  description = "Name of the Swarm Agents Auto Scaling Group"
  value       = aws_autoscaling_group.swarm_agents.name
}

output "swarm_agents_asg_arn" {
  description = "ARN of the Swarm Agents Auto Scaling Group"
  value       = aws_autoscaling_group.swarm_agents.arn
}

# Database
output "postgres_cluster_endpoint" {
  description = "RDS cluster endpoint"
  value       = aws_rds_cluster.postgres.endpoint
}

output "postgres_cluster_reader_endpoint" {
  description = "RDS cluster reader endpoint"
  value       = aws_rds_cluster.postgres.reader_endpoint
}

output "postgres_cluster_identifier" {
  description = "RDS cluster identifier"
  value       = aws_rds_cluster.postgres.cluster_identifier
}

output "postgres_database_name" {
  description = "PostgreSQL database name"
  value       = aws_rds_cluster.postgres.database_name
}

output "postgres_master_username" {
  description = "PostgreSQL master username"
  value       = aws_rds_cluster.postgres.master_username
  sensitive   = true
}

output "postgres_master_user_secret_arn" {
  description = "ARN of the secret containing PostgreSQL master password"
  value       = aws_rds_cluster.postgres.master_user_secret[0].secret_arn
  sensitive   = true
}

# Redis
output "redis_primary_endpoint" {
  description = "Redis primary endpoint"
  value       = aws_elasticache_replication_group.redis.configuration_endpoint_address
}

output "redis_port" {
  description = "Redis port"
  value       = aws_elasticache_replication_group.redis.port
}

output "redis_auth_token_secret_arn" {
  description = "ARN of the secret containing Redis auth token"
  value       = aws_secretsmanager_secret.redis_auth.arn
  sensitive   = true
}

# S3 Buckets
output "application_data_bucket" {
  description = "S3 bucket for application data"
  value       = aws_s3_bucket.application_data.bucket
}

output "backups_bucket" {
  description = "S3 bucket for backups"
  value       = aws_s3_bucket.backups.bucket
}

output "alb_logs_bucket" {
  description = "S3 bucket for ALB access logs"
  value       = aws_s3_bucket.alb_logs.bucket
}

# Backup
output "backup_vault_name" {
  description = "AWS Backup vault name"
  value       = aws_backup_vault.main.name
}

output "backup_plan_arn" {
  description = "AWS Backup plan ARN"
  value       = aws_backup_plan.main.arn
}

# Monitoring
output "cloudwatch_dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = var.cloudwatch_config.dashboard_enabled ? "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.main[0].dashboard_name}" : null
}

output "sns_alerts_topic_arn" {
  description = "SNS topic ARN for alerts"
  value       = aws_sns_topic.alerts.arn
}

# Security Groups
output "security_group_ids" {
  description = "Map of security group IDs"
  value = {
    alb                 = aws_security_group.alb.id
    swarm_queen        = aws_security_group.swarm_queen.id
    memory_coordinator = aws_security_group.memory_coordinator.id
    swarm_agents       = aws_security_group.swarm_agents.id
    postgres           = aws_security_group.postgres.id
    redis              = aws_security_group.redis.id
    monitoring         = aws_security_group.monitoring.id
    consul             = aws_security_group.consul.id
    bastion            = aws_security_group.bastion.id
  }
}

# KMS Keys
output "kms_key_arns" {
  description = "Map of KMS key ARNs"
  value = {
    rds        = aws_kms_key.rds.arn
    s3         = aws_kms_key.s3.arn
    ebs        = aws_kms_key.ebs.arn
    backup     = aws_kms_key.backup.arn
    cloudwatch = aws_kms_key.cloudwatch.arn
  }
}

# Connection Information
output "connection_info" {
  description = "Connection information for accessing the infrastructure"
  value = {
    bastion_host = {
      public_ip = aws_instance.bastion.public_ip
      ssh_command = "ssh -i /path/to/your/key.pem ec2-user@${aws_instance.bastion.public_ip}"
    }
    
    swarm_queen = {
      private_ip = aws_instance.swarm_queen.private_ip
      api_url = "http://${aws_instance.swarm_queen.private_ip}:8080"
      metrics_url = "http://${aws_instance.swarm_queen.private_ip}:8001"
      ssh_via_bastion = "ssh -i /path/to/your/key.pem -J ec2-user@${aws_instance.bastion.public_ip} ec2-user@${aws_instance.swarm_queen.private_ip}"
    }
    
    memory_coordinator = {
      private_ip = aws_instance.memory_coordinator.private_ip
      api_url = "http://${aws_instance.memory_coordinator.private_ip}:8002"
      ssh_via_bastion = "ssh -i /path/to/your/key.pem -J ec2-user@${aws_instance.bastion.public_ip} ec2-user@${aws_instance.memory_coordinator.private_ip}"
    }
    
    monitoring = {
      private_ip = aws_instance.monitoring.private_ip
      grafana_url = "http://${aws_instance.monitoring.private_ip}:3000"
      prometheus_url = "http://${aws_instance.monitoring.private_ip}:9090"
      ssh_via_bastion = "ssh -i /path/to/your/key.pem -J ec2-user@${aws_instance.bastion.public_ip} ec2-user@${aws_instance.monitoring.private_ip}"
    }
    
    consul = {
      private_ip = aws_instance.consul.private_ip
      ui_url = "http://${aws_instance.consul.private_ip}:8500"
      ssh_via_bastion = "ssh -i /path/to/your/key.pem -J ec2-user@${aws_instance.bastion.public_ip} ec2-user@${aws_instance.consul.private_ip}"
    }
  }
  sensitive = true
}

# Environment Configuration
output "environment_config" {
  description = "Environment configuration for application deployment"
  value = {
    environment = var.environment
    aws_region = var.aws_region
    vpc_cidr = var.vpc_cidr
    
    database = {
      endpoint = aws_rds_cluster.postgres.endpoint
      database = aws_rds_cluster.postgres.database_name
      username = aws_rds_cluster.postgres.master_username
      port = 5432
    }
    
    redis = {
      endpoint = aws_elasticache_replication_group.redis.configuration_endpoint_address
      port = aws_elasticache_replication_group.redis.port
      cluster_mode = true
    }
    
    consul = {
      endpoint = aws_instance.consul.private_ip
      port = 8500
    }
    
    load_balancer = {
      dns_name = aws_lb.main.dns_name
      internal_dns_name = aws_lb.internal.dns_name
    }
    
    storage = {
      application_bucket = aws_s3_bucket.application_data.bucket
      backup_bucket = aws_s3_bucket.backups.bucket
    }
  }
  sensitive = true
}

# Cost Optimization Information
output "cost_optimization" {
  description = "Information for cost optimization"
  value = {
    estimated_monthly_cost = {
      ec2_instances = "~$400-600 (depending on usage)"
      rds_cluster = "~$200-300"
      elasticache = "~$50-100"
      data_transfer = "~$50-150"
      storage = "~$100-200"
      load_balancer = "~$20-30"
      total_estimate = "~$820-1380"
    }
    
    cost_optimization_tips = [
      "Use Spot Instances for non-critical agents (enable var.enable_spot_instances)",
      "Monitor EBS volumes and resize as needed",
      "Set up lifecycle policies for S3 data",
      "Use Reserved Instances for stable workloads",
      "Monitor CloudWatch costs and optimize log retention",
      "Review and right-size instances based on actual usage"
    ]
  }
}

# Disaster Recovery Information
output "disaster_recovery" {
  description = "Disaster recovery information"
  value = {
    backup_schedule = var.backup_config.backup_schedule
    backup_retention = "${var.backup_config.retention_days} days"
    cross_region_replication = var.backup_config.copy_to_destination
    replica_region = var.backup_config.destination_region
    
    recovery_procedures = [
      "Database: Restore from automated RDS snapshots or Aurora backups",
      "Application Data: Restore from S3 versioned objects",
      "Configuration: Redeploy from Terraform state",
      "Monitoring Data: Prometheus data backed up daily to S3"
    ]
  }
}