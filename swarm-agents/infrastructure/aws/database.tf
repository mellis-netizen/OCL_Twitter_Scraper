# TGE Swarm Database Configuration
# High-availability PostgreSQL and Redis cluster with automated backups

# DB Subnet Group for RDS
resource "aws_db_subnet_group" "postgres" {
  name       = "${local.name_prefix}-postgres-subnet-group"
  subnet_ids = aws_subnet.database[*].id
  
  tags = {
    Name = "${local.name_prefix}-postgres-subnet-group"
  }
}

# RDS Aurora PostgreSQL Cluster
resource "aws_rds_cluster" "postgres" {
  cluster_identifier      = "${local.name_prefix}-postgres-cluster"
  engine                 = "aurora-postgresql"
  engine_version         = var.postgres_config.engine_version
  database_name          = "tge_swarm"
  master_username        = "swarm_user"
  manage_master_user_password = true
  
  db_subnet_group_name   = aws_db_subnet_group.postgres.name
  vpc_security_group_ids = [aws_security_group.postgres.id]
  
  backup_retention_period = var.postgres_config.backup_retention_period
  preferred_backup_window = var.postgres_config.backup_window
  preferred_maintenance_window = var.postgres_config.maintenance_window
  
  # Encryption
  storage_encrypted = true
  kms_key_id       = aws_kms_key.rds.arn
  
  # Performance Insights
  enabled_cloudwatch_logs_exports = ["postgresql"]
  
  # Backup configuration
  copy_tags_to_snapshot = true
  deletion_protection   = var.postgres_config.deletion_protection
  
  # Enhanced monitoring
  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.postgres.name
  
  tags = {
    Name = "${local.name_prefix}-postgres-cluster"
    Environment = var.environment
  }
  
  lifecycle {
    ignore_changes = [
      master_password
    ]
  }
}

# RDS Cluster Parameter Group
resource "aws_rds_cluster_parameter_group" "postgres" {
  family = "aurora-postgresql15"
  name   = "${local.name_prefix}-postgres-cluster-params"
  
  # Performance tuning parameters
  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }
  
  parameter {
    name  = "log_statement"
    value = "all"
  }
  
  parameter {
    name  = "log_min_duration_statement"
    value = "1000"  # Log queries taking more than 1 second
  }
  
  parameter {
    name  = "max_connections"
    value = "200"
  }
  
  tags = {
    Name = "${local.name_prefix}-postgres-cluster-params"
  }
}

# RDS Cluster Instances
resource "aws_rds_cluster_instance" "postgres_primary" {
  identifier         = "${local.name_prefix}-postgres-primary"
  cluster_identifier = aws_rds_cluster.postgres.id
  instance_class     = var.postgres_config.instance_class
  engine             = aws_rds_cluster.postgres.engine
  engine_version     = aws_rds_cluster.postgres.engine_version
  
  performance_insights_enabled = true
  monitoring_interval          = 60
  monitoring_role_arn         = aws_iam_role.rds_enhanced_monitoring.arn
  
  tags = {
    Name = "${local.name_prefix}-postgres-primary"
    Role = "Primary"
  }
}

resource "aws_rds_cluster_instance" "postgres_replica" {
  count = var.postgres_config.multi_az ? 1 : 0
  
  identifier         = "${local.name_prefix}-postgres-replica"
  cluster_identifier = aws_rds_cluster.postgres.id
  instance_class     = var.postgres_config.instance_class
  engine             = aws_rds_cluster.postgres.engine
  engine_version     = aws_rds_cluster.postgres.engine_version
  
  performance_insights_enabled = true
  monitoring_interval          = 60
  monitoring_role_arn         = aws_iam_role.rds_enhanced_monitoring.arn
  
  tags = {
    Name = "${local.name_prefix}-postgres-replica"
    Role = "Replica"
  }
}

# ElastiCache Subnet Group
resource "aws_elasticache_subnet_group" "redis" {
  name       = "${local.name_prefix}-redis-subnet-group"
  subnet_ids = aws_subnet.database[*].id
  
  tags = {
    Name = "${local.name_prefix}-redis-subnet-group"
  }
}

# ElastiCache Redis Replication Group
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id         = "${local.name_prefix}-redis"
  description                  = "TGE Swarm Redis Cluster"
  port                        = var.redis_config.port
  parameter_group_name        = var.redis_config.parameter_group_name
  node_type                   = var.redis_config.node_type
  num_cache_clusters          = var.redis_config.num_cache_clusters
  
  engine_version              = var.redis_config.engine_version
  
  # High Availability
  automatic_failover_enabled  = var.redis_config.automatic_failover_enabled
  multi_az_enabled           = var.redis_config.multi_az_enabled
  
  # Security
  subnet_group_name          = aws_elasticache_subnet_group.redis.name
  security_group_ids         = [aws_security_group.redis.id]
  at_rest_encryption_enabled = var.redis_config.at_rest_encryption_enabled
  transit_encryption_enabled = var.redis_config.transit_encryption_enabled
  auth_token                 = var.redis_config.transit_encryption_enabled ? random_password.redis_auth.result : null
  
  # Maintenance
  maintenance_window          = "sun:03:00-sun:04:00"
  snapshot_retention_limit    = 7
  snapshot_window            = "02:00-03:00"
  
  # Performance
  data_tiering_enabled       = false
  
  tags = {
    Name = "${local.name_prefix}-redis-cluster"
    Environment = var.environment
  }
  
  lifecycle {
    ignore_changes = [
      auth_token
    ]
  }
}

# ElastiCache Parameter Group for Redis
resource "aws_elasticache_parameter_group" "redis" {
  family = "redis7"
  name   = "${local.name_prefix}-redis-params"
  
  # Performance parameters
  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }
  
  parameter {
    name  = "timeout"
    value = "300"
  }
  
  parameter {
    name  = "tcp-keepalive"
    value = "300"
  }
  
  tags = {
    Name = "${local.name_prefix}-redis-params"
  }
}

# Random password for Redis authentication
resource "random_password" "redis_auth" {
  length  = 32
  special = true
}

# Store Redis auth token in Secrets Manager
resource "aws_secretsmanager_secret" "redis_auth" {
  name = "${local.name_prefix}-redis-auth-token"
  
  tags = {
    Name = "${local.name_prefix}-redis-auth"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "redis_auth" {
  secret_id     = aws_secretsmanager_secret.redis_auth.id
  secret_string = random_password.redis_auth.result
}

# KMS Key for RDS encryption
resource "aws_kms_key" "rds" {
  description             = "KMS key for RDS encryption"
  deletion_window_in_days = 7
  
  tags = {
    Name = "${local.name_prefix}-rds-kms"
    Environment = var.environment
  }
}

resource "aws_kms_alias" "rds" {
  name          = "alias/${local.name_prefix}-rds"
  target_key_id = aws_kms_key.rds.key_id
}

# IAM Role for RDS Enhanced Monitoring
resource "aws_iam_role" "rds_enhanced_monitoring" {
  name = "${local.name_prefix}-rds-enhanced-monitoring"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "rds_enhanced_monitoring" {
  role       = aws_iam_role.rds_enhanced_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# RDS Cluster Parameter Group for optimized performance
resource "aws_db_parameter_group" "postgres_instance" {
  family = "aurora-postgresql15"
  name   = "${local.name_prefix}-postgres-instance-params"
  
  # Connection and memory parameters
  parameter {
    name  = "shared_buffers"
    value = "{DBInstanceClassMemory/32768}"  # 25% of available memory
  }
  
  parameter {
    name  = "effective_cache_size"
    value = "{DBInstanceClassMemory/10922}"  # 75% of available memory
  }
  
  parameter {
    name  = "work_mem"
    value = "4096"  # 4MB
  }
  
  parameter {
    name  = "maintenance_work_mem"
    value = "65536"  # 64MB
  }
  
  # WAL and checkpoint parameters
  parameter {
    name  = "wal_buffers"
    value = "16384"  # 16MB
  }
  
  parameter {
    name  = "checkpoint_completion_target"
    value = "0.9"
  }
  
  # Query planner parameters
  parameter {
    name  = "random_page_cost"
    value = "1.1"  # For SSD storage
  }
  
  parameter {
    name  = "seq_page_cost"
    value = "1.0"
  }
  
  tags = {
    Name = "${local.name_prefix}-postgres-instance-params"
  }
}

# CloudWatch Alarms for Database Monitoring
resource "aws_cloudwatch_metric_alarm" "rds_cpu_high" {
  alarm_name          = "${local.name_prefix}-rds-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors RDS cpu utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    DBClusterIdentifier = aws_rds_cluster.postgres.cluster_identifier
  }
  
  tags = {
    Name = "${local.name_prefix}-rds-cpu-alarm"
  }
}

resource "aws_cloudwatch_metric_alarm" "redis_cpu_high" {
  alarm_name          = "${local.name_prefix}-redis-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors Redis cpu utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.redis.replication_group_id
  }
  
  tags = {
    Name = "${local.name_prefix}-redis-cpu-alarm"
  }
}

# SNS Topic for Database Alerts
resource "aws_sns_topic" "alerts" {
  name = "${local.name_prefix}-database-alerts"
  
  tags = {
    Name = "${local.name_prefix}-database-alerts"
    Environment = var.environment
  }
}