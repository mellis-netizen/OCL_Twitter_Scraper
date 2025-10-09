# TGE Swarm AWS Infrastructure

This directory contains the complete AWS infrastructure as code for deploying the TGE Swarm Optimization System on AWS EC2 with high availability, security, and monitoring.

## Architecture Overview

The infrastructure deploys a production-ready TGE Swarm system with the following components:

### Core Services
- **Swarm Queen Orchestrator** - Main coordination service (t3.large)
- **Memory Coordinator** - Manages shared memory state (t3.medium)
- **Swarm Agents** - Auto-scaling group of worker agents (t3.small)
- **Service Discovery** - Consul for service registration and discovery

### Infrastructure Services
- **Application Load Balancer** - Public-facing load balancer with SSL termination
- **Network Load Balancer** - Internal load balancing for service-to-service communication
- **PostgreSQL** - Aurora PostgreSQL cluster for persistent data
- **Redis** - ElastiCache Redis cluster for caching and real-time data
- **Monitoring Stack** - Prometheus, Grafana, AlertManager, Jaeger

### Security & Operations
- **Bastion Host** - Secure access to private instances
- **VPC with Multiple AZs** - Network isolation and high availability
- **Security Groups** - Fine-grained firewall rules
- **IAM Roles** - Principle of least privilege access
- **KMS Encryption** - Data encryption at rest and in transit
- **AWS Backup** - Automated backup and disaster recovery
- **CloudWatch** - Comprehensive monitoring and alerting

## Quick Start

### Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Terraform** >= 1.0 installed
3. **SSH Key Pair** created in AWS EC2 console
4. **S3 Bucket** for Terraform state (optional but recommended)

### 1. Configuration

Copy the example configuration and customize:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your specific settings:

```hcl
# Essential settings to change
key_pair_name = "your-ec2-keypair"
allowed_cidr_blocks = ["your.ip.address/32"]  # Restrict access
domain_name = "tge-swarm.yourdomain.com"      # Optional
certificate_arn = "arn:aws:acm:..."           # Optional SSL cert
```

### 2. Deployment

Use the deployment script for easy management:

```bash
# Make script executable
chmod +x deploy.sh

# Initialize Terraform (first time only)
./deploy.sh init

# Create and review execution plan
./deploy.sh plan

# Apply the infrastructure
./deploy.sh apply
```

### 3. Access the System

After deployment, get connection information:

```bash
./deploy.sh output connection_info
```

Access the services:
- **Grafana Dashboard**: `https://your-alb-dns/grafana` (admin/admin123)
- **Prometheus**: `https://your-alb-dns/prometheus`
- **Swarm Queen API**: `https://your-alb-dns/`

## File Structure

```
infrastructure/aws/
├── main.tf                 # Main Terraform configuration
├── variables.tf            # Input variables
├── outputs.tf             # Output values
├── vpc.tf                 # VPC and networking
├── security-groups.tf     # Security group rules
├── ec2.tf                 # EC2 instances and auto-scaling
├── load-balancer.tf       # Application and Network Load Balancers
├── database.tf            # RDS PostgreSQL and ElastiCache Redis
├── storage.tf             # S3 buckets, EBS volumes, backups
├── iam.tf                 # IAM roles and policies
├── monitoring.tf          # CloudWatch monitoring and alerting
├── deploy.sh              # Deployment automation script
├── terraform.tfvars.example # Configuration template
└── user-data/             # EC2 user data scripts
    ├── swarm-queen.sh
    ├── memory-coordinator.sh
    ├── swarm-agents.sh
    ├── monitoring.sh
    ├── consul.sh
    └── bastion.sh
```

## Instance Sizing Recommendations

### Production Environment
- **Swarm Queen**: t3.large (2 vCPU, 8GB RAM)
- **Memory Coordinator**: t3.medium (2 vCPU, 4GB RAM)
- **Swarm Agents**: t3.small (2 vCPU, 2GB RAM) - Auto-scaling 2-10 instances
- **Monitoring**: t3.medium (2 vCPU, 4GB RAM)
- **Database**: db.t3.medium (2 vCPU, 4GB RAM) - Aurora cluster
- **Cache**: cache.t3.micro (2 vCPU, 0.5GB RAM) - 3-node cluster

### Cost Optimization Options
- Enable spot instances for non-critical agents: `enable_spot_instances = true`
- Use smaller instance types for development: Adjust `instance_types` in variables
- Reduce backup retention: Modify `backup_config.retention_days`

## Security Features

### Network Security
- **VPC Isolation**: All resources in private subnets except load balancer
- **Security Groups**: Least-privilege access rules
- **Network ACLs**: Additional layer of network security
- **VPC Flow Logs**: Network traffic monitoring

### Data Security
- **Encryption at Rest**: RDS, EBS, S3 with KMS keys
- **Encryption in Transit**: SSL/TLS for all communications
- **Secrets Management**: AWS Secrets Manager for passwords
- **IAM Roles**: No hardcoded credentials

### Access Security
- **Bastion Host**: Secure access point with fail2ban and monitoring
- **SSH Key Authentication**: No password authentication
- **MFA Support**: Can be enabled on IAM users
- **VPN Integration**: Can be added for additional security

## Monitoring and Alerting

### Metrics Collection
- **Application Metrics**: Custom TGE metrics via Prometheus
- **Infrastructure Metrics**: CloudWatch for AWS services
- **System Metrics**: Node Exporter for OS-level metrics
- **Performance Metrics**: Response times, error rates, throughput

### Alerting Rules
- **High CPU Usage**: > 80% for 5 minutes
- **Memory Usage**: > 85% for 5 minutes
- **Disk Space**: < 20% free space
- **Database Connections**: High connection count
- **Application Errors**: Error rate threshold
- **Service Health**: Health check failures

### Dashboards
- **Grafana**: Custom dashboards for TGE metrics
- **CloudWatch**: AWS service dashboards
- **Jaeger**: Distributed tracing for debugging

## Backup and Disaster Recovery

### Automated Backups
- **RDS**: Point-in-time recovery with 7-day retention
- **EBS**: Daily snapshots via AWS Backup
- **Application Data**: S3 versioning and lifecycle policies
- **Configuration**: Terraform state in S3 with versioning

### Cross-Region Replication
- **S3 Backup Replication**: Optional cross-region backup copies
- **Database Replicas**: Aurora read replicas for disaster recovery
- **State Replication**: Terraform state backup to secondary region

### Recovery Procedures
1. **Database Recovery**: Restore from Aurora backup or snapshot
2. **Application Recovery**: Redeploy from Terraform with latest AMI
3. **Data Recovery**: Restore from S3 versioned objects
4. **Configuration Recovery**: Apply Terraform configuration

## Operations Guide

### Scaling Operations

#### Scale Agents Manually
```bash
# Scale to 8 instances
aws autoscaling set-desired-capacity \
    --auto-scaling-group-name tge-swarm-production-agents-asg \
    --desired-capacity 8
```

#### Update Instance Types
```bash
# Edit terraform.tfvars
vim terraform.tfvars

# Apply changes
./deploy.sh plan
./deploy.sh apply
```

### Monitoring Operations

#### View Logs
```bash
# CloudWatch Logs
aws logs tail /aws/ec2/swarm-queen --follow

# SSH to instance via bastion
ssh -J ec2-user@bastion-ip ec2-user@instance-ip
tail -f /app/logs/queen.log
```

#### Check Service Health
```bash
# Check auto-scaling group
aws autoscaling describe-auto-scaling-groups \
    --auto-scaling-group-names tge-swarm-production-agents-asg

# Check load balancer targets
aws elbv2 describe-target-health \
    --target-group-arn $(./deploy.sh output -raw target_group_arn)
```

### Maintenance Operations

#### Update Application Code
1. Build new AMI with updated code
2. Update launch template with new AMI ID
3. Trigger instance refresh in auto-scaling group

#### Database Maintenance
- **Minor Version Updates**: Automatic during maintenance window
- **Major Version Updates**: Manual with blue-green deployment
- **Parameter Changes**: Apply via RDS parameter groups

#### Security Updates
- **OS Updates**: Automatic via yum-cron
- **Application Updates**: Deploy new AMI
- **Security Patches**: Monitor AWS Security Bulletins

## Cost Management

### Estimated Monthly Costs (us-west-2)

| Service | Configuration | Estimated Cost |
|---------|---------------|----------------|
| EC2 Instances | 6 instances (mixed sizes) | $400-600 |
| RDS Aurora | db.t3.medium cluster | $200-300 |
| ElastiCache | 3x cache.t3.micro | $50-100 |
| Load Balancers | ALB + NLB | $20-30 |
| EBS Storage | 500GB total | $50-75 |
| S3 Storage | Backups and logs | $25-50 |
| Data Transfer | Regional + Internet | $50-150 |
| CloudWatch | Logs and metrics | $25-50 |
| **Total** | | **$820-1,355** |

### Cost Optimization

1. **Reserved Instances**: Save 30-50% on stable workloads
2. **Spot Instances**: Use for dev/test environments
3. **S3 Lifecycle**: Move old data to cheaper storage classes
4. **CloudWatch**: Optimize log retention periods
5. **EBS**: Right-size volumes and use gp3 for better price/performance

## Troubleshooting

### Common Issues

#### Deployment Failures
```bash
# Check Terraform state
terraform show

# Force unlock if state is locked
terraform force-unlock LOCK_ID

# Target specific resources
./deploy.sh plan --target aws_instance.swarm_queen
```

#### Application Issues
```bash
# Check instance health
aws ec2 describe-instance-status --instance-ids i-1234567890abcdef0

# SSH to troubleshoot
ssh -J ec2-user@bastion-ip ec2-user@instance-ip
sudo systemctl status tge-swarm-queen
journalctl -u tge-swarm-queen -f
```

#### Database Issues
```bash
# Check RDS cluster status
aws rds describe-db-clusters --db-cluster-identifier tge-swarm-production-postgres-cluster

# Check slow queries
# Connect to Aurora and check pg_stat_statements
```

#### Networking Issues
```bash
# Check security groups
aws ec2 describe-security-groups --group-ids sg-12345678

# Test connectivity
# From bastion host
nc -zv instance-ip 8080
```

### Support Contacts

- **Infrastructure Issues**: DevOps Team
- **Application Issues**: TGE Development Team
- **Security Issues**: Security Team
- **AWS Issues**: AWS Support (if subscribed)

## Advanced Configuration

### Multi-Region Setup
Enable multi-region deployment for disaster recovery:

```hcl
enable_multi_region = true
backup_config = {
  copy_to_destination = true
  destination_region = "us-east-1"
}
```

### Custom Domains
Configure custom domain with SSL:

```hcl
domain_name = "tge.yourdomain.com"
hosted_zone_id = "Z1234567890"
certificate_arn = "arn:aws:acm:us-west-2:123456789012:certificate/..."
```

### Advanced Monitoring
Enable additional monitoring features:

```hcl
cloudwatch_config = {
  enable_insights = true
  detailed_monitoring = true
}
enable_prometheus_monitoring = true
```

## License

This infrastructure code is part of the TGE Swarm project. See the main project LICENSE file for details.