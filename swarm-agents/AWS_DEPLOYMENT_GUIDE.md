# TGE Swarm AWS EC2 Deployment Guide

Complete guide for deploying the TGE Swarm Optimization System to AWS EC2 with production-ready infrastructure.

## 📋 Prerequisites

### 1. AWS Account Setup
- AWS account with appropriate permissions
- AWS CLI installed and configured
- Terraform installed (v1.6.0+)
- Git repository with GitHub Actions enabled

### 2. Required AWS Permissions
Your AWS user/role needs the following permissions:
- EC2 full access
- VPC management
- RDS/Aurora management
- ElastiCache management
- S3 bucket management
- IAM role creation
- CloudWatch access
- Application Load Balancer management
- Route53 (if using custom domain)

## 🔐 GitHub Secrets Configuration

Before deploying, configure these secrets in your GitHub repository:

### Navigate to: Repository → Settings → Secrets and Variables → Actions

```bash
# Required Secrets:
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_KEY_PAIR_NAME=your_ec2_key_pair_name
TF_STATE_BUCKET=your-terraform-state-bucket
TF_STATE_LOCK_TABLE=your-terraform-lock-table

# Optional Secrets (for custom domain):
DOMAIN_NAME=your-domain.com
CERTIFICATE_ARN=arn:aws:acm:region:account:certificate/cert-id
ALLOWED_CIDR_BLOCKS=0.0.0.0/0  # Your IP range for access
```

## 🏗️ Infrastructure Setup

### Step 1: Create Terraform State Resources

First, create the S3 bucket and DynamoDB table for Terraform state:

```bash
# Create S3 bucket for Terraform state
aws s3 mb s3://your-tge-swarm-terraform-state --region us-west-2

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket your-tge-swarm-terraform-state \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name tge-swarm-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-west-2
```

### Step 2: Create EC2 Key Pair

```bash
# Create key pair for EC2 access
aws ec2 create-key-pair \
  --key-name tge-swarm-keypair \
  --query 'KeyMaterial' \
  --output text > ~/.ssh/tge-swarm-keypair.pem

# Set correct permissions
chmod 400 ~/.ssh/tge-swarm-keypair.pem
```

### Step 3: Configure Domain (Optional)

If using a custom domain:

1. **Register domain** in Route53 or your DNS provider
2. **Request SSL certificate** in AWS Certificate Manager
3. **Validate certificate** via DNS or email
4. **Note the certificate ARN** for configuration

## 🚀 Deployment Options

### Option 1: Manual Deployment (Recommended for first time)

```bash
# 1. Clone repository
git clone <your-repo-url>
cd swarm-agents/infrastructure/aws

# 2. Configure terraform.tfvars
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your settings

# 3. Initialize Terraform
terraform init \
  -backend-config="bucket=your-tge-swarm-terraform-state" \
  -backend-config="key=production/terraform.tfstate" \
  -backend-config="region=us-west-2" \
  -backend-config="dynamodb_table=tge-swarm-terraform-locks"

# 4. Plan deployment
terraform plan

# 5. Apply infrastructure
terraform apply

# 6. Get connection information
terraform output connection_info
```

### Option 2: Automated Deployment via GitHub Actions

1. **Push changes** to main branch:
```bash
git add infrastructure/aws/
git commit -m "Deploy TGE Swarm infrastructure"
git push origin main
```

2. **Monitor deployment** in GitHub Actions tab

3. **Manual trigger** with specific environment:
   - Go to Actions → Deploy TGE Swarm to AWS → Run workflow
   - Select environment (staging/production)
   - Select action (plan/apply/destroy)

### Option 3: Quick Deploy Script

```bash
# Use the provided deployment script
cd infrastructure/aws
chmod +x deploy.sh

# Initialize (first time only)
./deploy.sh init

# Plan deployment
./deploy.sh plan

# Apply infrastructure
./deploy.sh apply

# Get status
./deploy.sh status

# Clean up (when needed)
./deploy.sh destroy
```

## 📊 Infrastructure Components

### Production Environment Includes:

**Compute Resources:**
- 1x Swarm Queen Orchestrator (t3.large)
- 1x Memory Coordinator (t3.medium)
- 5x Auto-scaling Swarm Agents (t3.small)
- 1x Monitoring Stack (t3.medium)
- 1x Bastion Host (t3.micro)

**Database & Cache:**
- Aurora PostgreSQL cluster (multi-AZ)
- ElastiCache Redis cluster
- Automated backups and monitoring

**Networking:**
- VPC with public/private subnets
- Application Load Balancer with SSL
- NAT Gateway for private subnet access
- Security groups with least privilege

**Storage:**
- EBS volumes for persistent data
- S3 buckets for backups and logs
- Cross-region backup replication

**Monitoring:**
- CloudWatch metrics and alarms
- Prometheus + Grafana dashboards
- Distributed tracing with Jaeger
- Log aggregation and analysis

## 🔗 Access Points

After deployment, access your services:

```bash
# Get connection information
terraform output connection_info

# Typical endpoints:
# Dashboard: https://your-load-balancer-dns/
# Grafana: https://your-load-balancer-dns:3000
# Prometheus: https://your-load-balancer-dns:9090
# API: https://your-load-balancer-dns/api
```

### SSH Access to Instances

```bash
# Connect to bastion host
ssh -i ~/.ssh/tge-swarm-keypair.pem ec2-user@<bastion-ip>

# From bastion, connect to private instances
ssh ec2-user@<private-instance-ip>
```

## 📈 Cost Optimization

### Expected Monthly Costs (us-west-2):

**Production Environment:**
- EC2 Instances: ~$240/month
- Aurora Database: ~$200/month
- ElastiCache: ~$50/month
- Load Balancer: ~$25/month
- Data Transfer: ~$50/month
- Storage: ~$30/month
- **Total: ~$595-820/month**

### Cost Reduction Strategies:

1. **Reserved Instances** (30-50% savings):
```bash
# Purchase 1-year reserved instances for stable workloads
aws ec2 purchase-reserved-instances-offering \
  --reserved-instances-offering-id <offering-id> \
  --instance-count 1
```

2. **Spot Instances** for development:
```hcl
# In terraform.tfvars
use_spot_instances = true
spot_price = "0.05"  # Maximum price per hour
```

3. **Auto-scaling optimization**:
```hcl
# Configure aggressive scaling policies
agent_min_size = 2
agent_max_size = 10
target_cpu_utilization = 70
```

## 🔧 Configuration Options

### Environment-Specific Settings

Edit `terraform.tfvars` for your environment:

```hcl
# Basic Configuration
aws_region = "us-west-2"
environment = "production"
project_name = "tge-swarm"

# Networking
availability_zones = ["us-west-2a", "us-west-2b", "us-west-2c"]
vpc_cidr = "10.0.0.0/16"
allowed_cidr_blocks = ["0.0.0.0/0"]  # Restrict this!

# Instance Configuration
swarm_queen_instance_type = "t3.large"
memory_coordinator_instance_type = "t3.medium"
swarm_agent_instance_type = "t3.small"
monitoring_instance_type = "t3.medium"

# Database Configuration
db_instance_class = "db.t3.medium"
db_allocated_storage = 100
db_backup_retention_period = 7

# Cache Configuration
cache_node_type = "cache.t3.micro"
cache_num_cache_nodes = 2

# SSL/Domain (optional)
domain_name = "tge-swarm.yourdomain.com"
certificate_arn = "arn:aws:acm:us-west-2:account:certificate/cert-id"

# Feature Flags
enable_monitoring = true
enable_backups = true
enable_multi_az = true
enable_encryption = true
```

## 🔍 Monitoring & Troubleshooting

### Health Checks

```bash
# Check system status
curl https://your-load-balancer-dns/health

# Check individual services
curl https://your-load-balancer-dns/api/health
curl https://your-load-balancer-dns/metrics
```

### Log Access

```bash
# CloudWatch Logs
aws logs describe-log-groups --log-group-name-prefix "/tge-swarm"

# SSH to instance and check Docker logs
ssh -i ~/.ssh/tge-swarm-keypair.pem ec2-user@<instance-ip>
docker logs tge-swarm-queen
docker logs tge-memory-coordinator
```

### Common Issues & Solutions

1. **Deployment fails with permissions error**:
   - Verify AWS credentials and permissions
   - Check IAM policies include all required services

2. **Cannot access dashboard**:
   - Check security group rules allow port 80/443
   - Verify load balancer health checks are passing

3. **High costs**:
   - Review instance types and scaling policies
   - Consider reserved instances for stable workloads
   - Enable detailed billing monitoring

4. **Performance issues**:
   - Check CloudWatch metrics for resource utilization
   - Scale up instance types or increase agent count
   - Review database performance insights

## 🔄 Maintenance & Updates

### Regular Maintenance Tasks

```bash
# Update system packages (via user data automation)
# Rotate logs (automatic via CloudWatch agent)
# Backup verification (automated daily)
# Security updates (automatic via unattended-upgrades)
```

### Rolling Updates

```bash
# Update infrastructure
terraform plan
terraform apply

# Update application (blue/green deployment)
# Handled automatically via GitHub Actions
```

### Backup & Recovery

```bash
# Manual backup
aws rds create-db-cluster-snapshot \
  --db-cluster-identifier tge-swarm-cluster \
  --db-cluster-snapshot-identifier manual-backup-$(date +%Y%m%d)

# Restore from backup
aws rds restore-db-cluster-from-snapshot \
  --db-cluster-identifier tge-swarm-cluster-restored \
  --snapshot-identifier backup-snapshot-id
```

## 🛡️ Security Best Practices

### Network Security
- VPC with private subnets for applications
- Security groups with minimal required access
- Bastion host for secure SSH access
- VPC Flow Logs enabled

### Data Security
- Encryption at rest for all storage
- Encryption in transit with SSL/TLS
- KMS key management
- Regular security updates

### Access Control
- IAM roles with least privilege
- No hardcoded credentials
- MFA enabled for AWS console access
- Regular access reviews

### Monitoring
- CloudTrail enabled for API logging
- CloudWatch alarms for security events
- Automated security scanning
- Regular vulnerability assessments

## 📞 Support & Troubleshooting

### Getting Help

1. **Check CloudWatch Logs**: Most issues are logged
2. **Review Terraform Output**: Infrastructure creation errors
3. **SSH to Instances**: Direct debugging access
4. **GitHub Actions Logs**: Deployment pipeline issues

### Emergency Procedures

```bash
# Emergency scale down (cost control)
terraform apply -var="agent_min_size=0" -var="agent_max_size=0"

# Emergency destroy (nuclear option)
terraform destroy -auto-approve

# Rollback to previous version
git revert <commit-hash>
git push origin main  # Triggers automatic redeployment
```

This comprehensive guide covers everything needed to deploy and maintain the TGE Swarm system on AWS EC2 with production-grade reliability and security.