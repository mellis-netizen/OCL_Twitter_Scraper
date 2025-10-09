# TGE Swarm Storage Configuration
# S3 buckets, EBS volumes, and backup storage for the swarm infrastructure

# S3 Bucket for Application Data and Logs
resource "aws_s3_bucket" "application_data" {
  bucket        = "${local.name_prefix}-app-data-${random_string.bucket_suffix.result}"
  force_destroy = false
  
  tags = {
    Name = "${local.name_prefix}-application-data"
    Environment = var.environment
    Purpose = "Application Data Storage"
  }
}

resource "aws_s3_bucket_versioning" "application_data" {
  bucket = aws_s3_bucket.application_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "application_data" {
  bucket = aws_s3_bucket.application_data.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "application_data" {
  bucket = aws_s3_bucket.application_data.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "application_data" {
  bucket = aws_s3_bucket.application_data.id
  
  rule {
    id     = "application_data_lifecycle"
    status = "Enabled"
    
    # Transition to IA after 30 days
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    
    # Transition to Glacier after 90 days
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
    
    # Delete after 2555 days (7 years)
    expiration {
      days = 2555
    }
    
    # Clean up incomplete multipart uploads
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
    
    # Handle non-current versions
    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }
    
    noncurrent_version_transition {
      noncurrent_days = 90
      storage_class   = "GLACIER"
    }
    
    noncurrent_version_expiration {
      noncurrent_days = 365
    }
  }
}

# S3 Bucket for Backups
resource "aws_s3_bucket" "backups" {
  bucket        = "${local.name_prefix}-backups-${random_string.bucket_suffix.result}"
  force_destroy = false
  
  tags = {
    Name = "${local.name_prefix}-backups"
    Environment = var.environment
    Purpose = "Backup Storage"
  }
}

resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "backups" {
  bucket = aws_s3_bucket.backups.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id
  
  rule {
    id     = "backup_lifecycle"
    status = "Enabled"
    
    # Keep current backups in Standard storage for 30 days
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    
    # Move to Glacier after 90 days
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
    
    # Move to Deep Archive after 1 year
    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }
    
    # Keep backups for 7 years (compliance requirement)
    expiration {
      days = 2555
    }
    
    # Clean up incomplete multipart uploads
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
    
    # Handle non-current versions (keep for 90 days)
    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# Cross-region replication for backups (disaster recovery)
resource "aws_s3_bucket_replication_configuration" "backups" {
  count = var.backup_config.copy_to_destination ? 1 : 0
  
  role   = aws_iam_role.s3_replication[0].arn
  bucket = aws_s3_bucket.backups.id
  
  rule {
    id     = "backup_replication"
    status = "Enabled"
    
    destination {
      bucket        = aws_s3_bucket.backups_replica[0].arn
      storage_class = "STANDARD_IA"
      
      encryption_configuration {
        replica_kms_key_id = aws_kms_key.s3_replica[0].arn
      }
    }
  }
  
  depends_on = [aws_s3_bucket_versioning.backups]
}

# Replica bucket in different region for disaster recovery
resource "aws_s3_bucket" "backups_replica" {
  count = var.backup_config.copy_to_destination ? 1 : 0
  
  provider      = aws.replica
  bucket        = "${local.name_prefix}-backups-replica-${random_string.bucket_suffix.result}"
  force_destroy = false
  
  tags = {
    Name = "${local.name_prefix}-backups-replica"
    Environment = var.environment
    Purpose = "Backup Replication"
  }
}

resource "aws_s3_bucket_versioning" "backups_replica" {
  count = var.backup_config.copy_to_destination ? 1 : 0
  
  provider = aws.replica
  bucket   = aws_s3_bucket.backups_replica[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

# KMS Key for S3 encryption
resource "aws_kms_key" "s3" {
  description             = "KMS key for S3 bucket encryption"
  deletion_window_in_days = 7
  
  tags = {
    Name = "${local.name_prefix}-s3-kms"
    Environment = var.environment
  }
}

resource "aws_kms_alias" "s3" {
  name          = "alias/${local.name_prefix}-s3"
  target_key_id = aws_kms_key.s3.key_id
}

# KMS Key for replica region
resource "aws_kms_key" "s3_replica" {
  count = var.backup_config.copy_to_destination ? 1 : 0
  
  provider                = aws.replica
  description             = "KMS key for S3 replica bucket encryption"
  deletion_window_in_days = 7
  
  tags = {
    Name = "${local.name_prefix}-s3-replica-kms"
    Environment = var.environment
  }
}

resource "aws_kms_alias" "s3_replica" {
  count = var.backup_config.copy_to_destination ? 1 : 0
  
  provider      = aws.replica
  name          = "alias/${local.name_prefix}-s3-replica"
  target_key_id = aws_kms_key.s3_replica[0].key_id
}

# IAM Role for S3 Cross-Region Replication
resource "aws_iam_role" "s3_replication" {
  count = var.backup_config.copy_to_destination ? 1 : 0
  
  name = "${local.name_prefix}-s3-replication-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Name = "${local.name_prefix}-s3-replication-role"
  }
}

resource "aws_iam_role_policy" "s3_replication" {
  count = var.backup_config.copy_to_destination ? 1 : 0
  
  name = "${local.name_prefix}-s3-replication-policy"
  role = aws_iam_role.s3_replication[0].id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObjectVersionForReplication",
          "s3:GetObjectVersionAcl"
        ]
        Resource = "${aws_s3_bucket.backups.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.backups.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ReplicateObject",
          "s3:ReplicateDelete"
        ]
        Resource = "${aws_s3_bucket.backups_replica[0].arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = aws_kms_key.s3.arn
      },
      {
        Effect = "Allow"
        Action = [
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.s3_replica[0].arn
      }
    ]
  })
}

# EBS Snapshots for EC2 instances
resource "aws_ebs_snapshot" "queen_data" {
  volume_id = aws_ebs_volume.queen_data.id
  
  tags = {
    Name = "${local.name_prefix}-queen-data-snapshot"
    Environment = var.environment
    Type = "Manual"
  }
}

# EBS Volumes for persistent data
resource "aws_ebs_volume" "queen_data" {
  availability_zone = aws_instance.swarm_queen.availability_zone
  size              = 100
  type              = "gp3"
  iops              = 3000
  throughput        = 125
  encrypted         = true
  kms_key_id        = aws_kms_key.ebs.arn
  
  tags = {
    Name = "${local.name_prefix}-queen-data"
    Environment = var.environment
    Instance = "swarm-queen"
  }
}

resource "aws_volume_attachment" "queen_data" {
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.queen_data.id
  instance_id = aws_instance.swarm_queen.id
}

resource "aws_ebs_volume" "coordinator_data" {
  availability_zone = aws_instance.memory_coordinator.availability_zone
  size              = 50
  type              = "gp3"
  iops              = 3000
  throughput        = 125
  encrypted         = true
  kms_key_id        = aws_kms_key.ebs.arn
  
  tags = {
    Name = "${local.name_prefix}-coordinator-data"
    Environment = var.environment
    Instance = "memory-coordinator"
  }
}

resource "aws_volume_attachment" "coordinator_data" {
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.coordinator_data.id
  instance_id = aws_instance.memory_coordinator.id
}

resource "aws_ebs_volume" "monitoring_data" {
  availability_zone = aws_instance.monitoring.availability_zone
  size              = 200
  type              = "gp3"
  iops              = 3000
  throughput        = 125
  encrypted         = true
  kms_key_id        = aws_kms_key.ebs.arn
  
  tags = {
    Name = "${local.name_prefix}-monitoring-data"
    Environment = var.environment
    Instance = "monitoring"
  }
}

resource "aws_volume_attachment" "monitoring_data" {
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.monitoring_data.id
  instance_id = aws_instance.monitoring.id
}

# KMS Key for EBS encryption
resource "aws_kms_key" "ebs" {
  description             = "KMS key for EBS volume encryption"
  deletion_window_in_days = 7
  
  tags = {
    Name = "${local.name_prefix}-ebs-kms"
    Environment = var.environment
  }
}

resource "aws_kms_alias" "ebs" {
  name          = "alias/${local.name_prefix}-ebs"
  target_key_id = aws_kms_key.ebs.key_id
}

# AWS Backup Vault
resource "aws_backup_vault" "main" {
  name        = var.backup_config.backup_vault_name
  kms_key_arn = aws_kms_key.backup.arn
  
  tags = {
    Name = var.backup_config.backup_vault_name
    Environment = var.environment
  }
}

# KMS Key for AWS Backup
resource "aws_kms_key" "backup" {
  description             = "KMS key for AWS Backup"
  deletion_window_in_days = 7
  
  tags = {
    Name = "${local.name_prefix}-backup-kms"
    Environment = var.environment
  }
}

resource "aws_kms_alias" "backup" {
  name          = "alias/${local.name_prefix}-backup"
  target_key_id = aws_kms_key.backup.key_id
}

# AWS Backup Plan
resource "aws_backup_plan" "main" {
  name = "${local.name_prefix}-backup-plan"
  
  rule {
    rule_name         = "daily_backups"
    target_vault_name = aws_backup_vault.main.name
    schedule          = var.backup_config.backup_schedule
    
    start_window      = 60
    completion_window = 300
    
    lifecycle {
      cold_storage_after = 30
      delete_after       = var.backup_config.retention_days
    }
    
    recovery_point_tags = {
      Environment = var.environment
      CreatedBy   = "AWS-Backup"
    }
  }
  
  advanced_backup_setting {
    backup_options = {
      WindowsVSS = "enabled"
    }
    resource_type = "EC2"
  }
  
  tags = {
    Name = "${local.name_prefix}-backup-plan"
    Environment = var.environment
  }
}

# AWS Backup Selection
resource "aws_backup_selection" "main" {
  iam_role_arn = aws_iam_role.backup.arn
  name         = "${local.name_prefix}-backup-selection"
  plan_id      = aws_backup_plan.main.id
  
  resources = [
    aws_rds_cluster.postgres.arn,
    aws_ebs_volume.queen_data.arn,
    aws_ebs_volume.coordinator_data.arn,
    aws_ebs_volume.monitoring_data.arn
  ]
  
  condition {
    string_equals {
      key   = "Environment"
      value = var.environment
    }
  }
}

# Provider for replica region
provider "aws" {
  alias  = "replica"
  region = var.backup_config.destination_region
  
  default_tags {
    tags = {
      Project     = "TGE-Swarm"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = "TGE-Swarm-Team"
      Region      = "Replica"
    }
  }
}