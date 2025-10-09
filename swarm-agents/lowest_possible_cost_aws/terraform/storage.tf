# Storage Configuration for Ultra-Low-Cost Deployment
# Minimal S3 usage with lifecycle policies

# S3 bucket for backups (optional, only if enabled)
resource "aws_s3_bucket" "backups" {
  count  = var.enable_backup_to_s3 ? 1 : 0
  bucket = "${local.name_prefix}-backups-${random_id.bucket_suffix.hex}"

  tags = {
    Name        = "${local.name_prefix}-backups"
    Environment = var.environment
    Purpose     = "Backups"
  }
}

# Random ID for bucket naming
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# Bucket versioning (disabled to save costs)
resource "aws_s3_bucket_versioning" "backups" {
  count  = var.enable_backup_to_s3 ? 1 : 0
  bucket = aws_s3_bucket.backups[0].id
  
  versioning_configuration {
    status = "Disabled"
  }
}

# Bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  count  = var.enable_backup_to_s3 ? 1 : 0
  bucket = aws_s3_bucket.backups[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"  # Free encryption
    }
  }
}

# Lifecycle policy for cost optimization
resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  count  = var.enable_backup_to_s3 ? 1 : 0
  bucket = aws_s3_bucket.backups[0].id

  rule {
    id     = "backup_lifecycle"
    status = "Enabled"

    # Delete old backups
    expiration {
      days = var.backup_retention_days
    }

    # Transition to cheaper storage classes
    transition {
      days          = 1
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 3
      storage_class = "GLACIER"
    }

    # Delete incomplete multipart uploads
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# Block public access (security best practice)
resource "aws_s3_bucket_public_access_block" "backups" {
  count  = var.enable_backup_to_s3 ? 1 : 0
  bucket = aws_s3_bucket.backups[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}