# TGE Swarm Ultra-Low-Cost AWS Deployment

**Cost Optimization Engineer: Claude**

This directory contains a complete ultra-low-cost AWS infrastructure deployment for the TGE Swarm system, targeting monthly costs under $100-150 while maintaining full functionality.

## 🎯 Cost Optimization Features

### Core Cost Savings
- **Spot Instances**: 60-90% savings on compute costs
- **Single AZ Deployment**: Eliminates cross-AZ data transfer charges
- **Consolidated Services**: All services run in minimal containers
- **Auto-Shutdown**: Automatic shutdown during off-hours
- **Minimal Storage**: Optimized EBS volumes with lifecycle policies
- **Local Backups**: Avoids S3 storage costs by default

### Resource Optimization
- **Multi-Service Containers**: Reduces instance count
- **Aggressive Resource Limits**: Prevents cost overruns
- **Spot Interruption Handling**: Graceful shutdown with data preservation
- **Cost Monitoring**: Real-time cost tracking and alerts

## 💰 Estimated Monthly Costs

| Component | Cost (USD) | Notes |
|-----------|------------|-------|
| Main Instance (t3.small spot) | ~$4.50 | 70% savings vs on-demand |
| Backup Instance (t3.nano) | ~$3.80 | Minimal failover instance |
| EBS Storage (20GB gp3) | ~$2.00 | Optimized storage type |
| Application Load Balancer | ~$16.20 | Required for high availability |
| Data Transfer | ~$5.00 | Estimated moderate usage |
| CloudWatch Basic | ~$3.50 | Essential monitoring only |
| SNS Notifications | ~$0.50 | Cost and system alerts |
| Lambda (cost optimizer) | ~$0.20 | Serverless cost management |
| S3 Backups (optional) | ~$1.00 | Disabled by default |
| **TOTAL ESTIMATED** | **~$35-45** | **Excluding data transfer overages** |

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        AWS Region (us-east-1)              │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                Single AZ Deployment                 │    │
│  │                                                     │    │
│  │  ┌──────────────────┐  ┌──────────────────┐        │    │
│  │  │   Main Instance  │  │  Backup Instance │        │    │
│  │  │   (t3.small)     │  │   (t3.nano)      │        │    │
│  │  │   Spot Pricing   │  │   On-Demand      │        │    │
│  │  │                  │  │                  │        │    │
│  │  │  ┌────────────┐  │  │  ┌────────────┐  │        │    │
│  │  │  │ All-in-One │  │  │  │   Monitor  │  │        │    │
│  │  │  │ Container  │  │  │  │  & Backup  │  │        │    │
│  │  │  │            │  │  │  │            │  │        │    │
│  │  │  │ • Queen    │  │  │  │ • Health   │  │        │    │
│  │  │  │ • Agents   │  │  │  │ • Failover │  │        │    │
│  │  │  │ • Memory   │  │  │  │ • Sync     │  │        │    │
│  │  │  │ • DB       │  │  │  │            │  │        │    │
│  │  │  │ • Cache    │  │  │  │            │  │        │    │
│  │  │  │ • Monitor  │  │  │  │            │  │        │    │
│  │  │  └────────────┘  │  │  └────────────┘  │        │    │
│  │  └──────────────────┘  └──────────────────┘        │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │            Application Load Balancer                │    │
│  │         (HTTP/HTTPS with SSL termination)          │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## 📂 Directory Structure

```
lowest_possible_cost_aws/
├── terraform/              # Infrastructure as Code
│   ├── main.tf             # Main Terraform configuration
│   ├── variables.tf        # Input variables
│   ├── vpc.tf              # VPC and networking
│   ├── ec2.tf              # EC2 instances and Auto Scaling
│   ├── security-groups.tf  # Security group rules
│   ├── load-balancer.tf    # Application Load Balancer
│   ├── ssl.tf              # SSL certificate management
│   ├── iam.tf              # IAM roles and policies
│   ├── storage.tf          # S3 and EBS configuration
│   ├── monitoring.tf       # CloudWatch and cost monitoring
│   └── outputs.tf          # Output values
├── docker/                 # Container definitions
│   ├── docker-compose-cost-optimized.yml
│   ├── Dockerfile.all-in-one
│   ├── Dockerfile.backup
│   └── supervisord.conf
├── scripts/                # Deployment and management scripts
│   ├── deploy.sh           # Main deployment script
│   ├── user-data-main.sh   # EC2 user data for main instance
│   ├── user-data-backup.sh # EC2 user data for backup instance
│   ├── cost-optimizer.py   # Cost monitoring and optimization
│   ├── health-check.sh     # Health check script
│   ├── start-all-services.sh
│   ├── backup-local.sh     # Local backup script
│   └── restore.sh          # Restore script
├── config/                 # Configuration files
│   ├── nginx/              # NGINX reverse proxy config
│   ├── backup-crontab      # Backup scheduling
│   └── monitoring/         # Monitoring configurations
├── monitoring/             # Cost and system monitoring
└── docs/                   # Additional documentation
```

## 🚀 Quick Start

### Prerequisites

1. **AWS CLI configured** with appropriate permissions
2. **Terraform** >= 1.0 installed
3. **Docker** and **Docker Compose** installed
4. **EC2 Key Pair** created in target region

### Basic Deployment

```bash
# 1. Clone the repository
cd swarm-agents/lowest_possible_cost_aws

# 2. Deploy with minimal configuration
./scripts/deploy.sh --key-name your-aws-key --alert-email admin@yourcompany.com

# 3. Wait for deployment (5-10 minutes)
# 4. Access your TGE Swarm at the provided URL
```

### Advanced Deployment

```bash
# Deploy with custom domain and enhanced monitoring
./scripts/deploy.sh \
  --key-name your-aws-key \
  --domain myswarm.com \
  --alert-email admin@myswarm.com \
  --cost-threshold 100 \
  --enable-s3-backups \
  --region us-west-2
```

## 🔧 Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_REGION` | `us-east-1` | AWS region (cheapest: us-east-1) |
| `AUTO_SHUTDOWN_ENABLED` | `true` | Enable auto-shutdown |
| `AUTO_SHUTDOWN_SCHEDULE` | `0 22 * * *` | Shutdown at 10 PM UTC |
| `AUTO_STARTUP_SCHEDULE` | `0 6 * * 1-5` | Start at 6 AM UTC, weekdays |
| `COST_THRESHOLD` | `150` | Monthly cost alert threshold |
| `ENABLE_S3_BACKUPS` | `false` | Enable S3 backup sync |
| `BACKUP_RETENTION_DAYS` | `7` | Local backup retention |

### Terraform Variables

Key variables in `terraform.tfvars`:

```hcl
# Required
key_name = "your-aws-key"

# Optional cost optimizations
auto_shutdown_enabled = true
enable_detailed_monitoring = false
storage_size = 20
backup_retention_days = 7

# Features
enable_monitoring_stack = true
enable_backup_to_s3 = false

# Security
allowed_cidr_blocks = ["0.0.0.0/0"]  # Restrict in production
```

## 🛡️ Security Considerations

### Network Security
- **Single AZ**: Reduces attack surface but limits availability
- **Security Groups**: Minimal open ports (22, 80, 443, 8080)
- **SSL/TLS**: Enforced HTTPS with free ACM certificates
- **Rate Limiting**: NGINX-based request throttling

### Access Control
- **IAM Roles**: Principle of least privilege
- **SSH Keys**: Key-based authentication only
- **Basic Auth**: Prometheus access protected
- **Network ACLs**: Default restrictive rules

### Data Protection
- **EBS Encryption**: All volumes encrypted at rest
- **Backup Encryption**: Compressed and optionally encrypted
- **SSL Transit**: All data in transit encrypted

## 📊 Monitoring and Alerting

### Cost Monitoring
- **Real-time tracking**: CloudWatch cost metrics
- **Automated alerts**: SNS notifications when over budget
- **Daily reports**: Cost breakdown by service
- **Auto-shutdown**: Prevents runaway costs

### System Monitoring
- **Health checks**: Automated service health monitoring
- **Performance metrics**: CPU, memory, disk usage
- **Log aggregation**: Centralized logging with retention
- **Grafana dashboards**: Visual monitoring interface

### Alert Channels
- **Email notifications**: Cost and system alerts
- **SNS integration**: Programmable alert handling
- **CloudWatch alarms**: Automated threshold monitoring

## 🔄 Backup and Recovery

### Backup Strategy
- **Daily backups**: Automated at 2 AM UTC
- **Local storage**: No additional S3 costs by default
- **7-day retention**: Balances protection and cost
- **Compression**: Reduces storage requirements

### Backup Components
- **PostgreSQL database**: Full dump with schema
- **Redis data**: RDB snapshots
- **Application data**: SAFLA memory and configuration
- **System logs**: Recent logs for troubleshooting

### Recovery Options
```bash
# List available backups
./scripts/restore.sh --help

# Restore from latest backup
./scripts/restore.sh latest

# Restore only database
./scripts/restore.sh --database-only latest

# Full restore with current state backup
./scripts/restore.sh --backup-current --force latest
```

## ⚡ Performance Optimization

### Resource Allocation
- **CPU limits**: Prevents cost overruns
- **Memory optimization**: Efficient allocation across services
- **I/O optimization**: GP3 storage for better price/performance
- **Network optimization**: Single AZ reduces latency

### Service Consolidation
- **All-in-one container**: Reduces overhead
- **Shared resources**: Maximizes utilization
- **Process supervision**: Automatic restart on failures
- **Health monitoring**: Proactive issue detection

## 🔧 Troubleshooting

### Common Issues

#### Spot Instance Interruption
```bash
# Check interruption logs
tail -f /var/log/spot-monitor.log

# Manual backup before interruption
/opt/tge-swarm/scripts/backup-before-interruption.sh
```

#### High Costs
```bash
# Check current month costs
python3 /app/cost-optimizer.py

# Review cost breakdown in CloudWatch
# Check for unexpected data transfer
```

#### Service Health Issues
```bash
# Run health check
/app/health-check.sh

# Check service logs
docker-compose logs tge-swarm-all-in-one

# Restart services
docker-compose restart
```

#### Database Connection Issues
```bash
# Check PostgreSQL status
docker exec tge-postgres-cost-optimized pg_isready

# Check Redis status
docker exec tge-redis-cost-optimized redis-cli ping

# Review connection logs
tail -f /app/logs/database.log
```

### Emergency Procedures

#### Complete System Failure
1. Access backup instance
2. Run emergency restore: `/opt/backup/emergency-restore.sh`
3. Point DNS to backup instance
4. Investigate main instance issues

#### Data Loss Recovery
1. Stop all services
2. Restore from latest backup: `./scripts/restore.sh latest`
3. Verify data integrity
4. Restart services

## 📈 Scaling Considerations

### Vertical Scaling
- **Instance types**: Easy upgrade to t3.medium/large
- **Storage expansion**: EBS volume resize
- **Memory limits**: Adjust container resources

### Horizontal Scaling
- **Multi-AZ**: Add second AZ for high availability
- **Load balancer**: Already configured for multiple targets
- **Database**: Consider RDS Multi-AZ for production

### Cost Impact
- **t3.medium**: ~$9/month (spot) vs $4.50
- **Multi-AZ**: +$20-30/month for cross-AZ charges
- **RDS**: +$15-25/month for managed database

## 🔮 Future Enhancements

### Potential Optimizations
- **Reserved Instances**: For stable workloads
- **Savings Plans**: For predictable usage
- **ARM instances**: Graviton2 for additional savings
- **Container optimization**: Further resource reduction

### Advanced Features
- **CI/CD integration**: Automated deployments
- **Blue-green deployments**: Zero-downtime updates
- **Advanced monitoring**: Custom metrics and dashboards
- **Auto-scaling**: Dynamic resource adjustment

## 📞 Support and Maintenance

### Regular Maintenance
- **Weekly**: Review cost reports and optimize
- **Monthly**: Update security patches
- **Quarterly**: Review and tune resource allocation

### Monitoring Checklist
- [ ] Cost alerts configured and working
- [ ] Backup schedule running successfully
- [ ] Health checks passing
- [ ] SSL certificates not expiring
- [ ] Security groups properly configured

### Emergency Contacts
- **Cost alerts**: Check email for threshold breaches
- **System alerts**: Monitor SNS notifications
- **Manual intervention**: SSH access via backup instance

## 📚 Additional Resources

- [AWS Cost Optimization Best Practices](https://aws.amazon.com/aws-cost-management/aws-cost-optimization/)
- [EC2 Spot Instance Best Practices](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-best-practices.html)
- [Terraform AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Docker Compose Best Practices](https://docs.docker.com/compose/production/)

---

**⚠️ Important Notes:**

1. **This is a cost-optimized deployment** prioritizing savings over high availability
2. **Spot instances may be interrupted** - ensure critical data is backed up
3. **Single AZ deployment** reduces availability but minimizes costs
4. **Monitor costs closely** during initial deployment to validate estimates
5. **Production use** may require additional redundancy and security measures

**🎯 Target Use Cases:**
- Development and testing environments
- Small-scale production deployments
- Cost-conscious proof-of-concepts
- Learning and experimentation

For production environments requiring high availability, consider the standard multi-AZ deployment in the `infrastructure/aws` directory.