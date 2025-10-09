# 🚀 Quick AWS Deployment Guide

Deploy your TGE Swarm to AWS EC2 in 3 simple steps!

## Prerequisites (5 minutes)

1. **Install AWS CLI**:
   ```bash
   # macOS
   brew install awscli
   
   # Linux
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip && sudo ./aws/install
   ```

2. **Install Terraform**:
   ```bash
   # macOS
   brew install terraform
   
   # Linux
   wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
   unzip terraform_1.6.0_linux_amd64.zip && sudo mv terraform /usr/local/bin/
   ```

3. **Configure AWS credentials**:
   ```bash
   aws configure
   # Enter: Access Key ID, Secret Access Key, Region (us-west-2), Output format (json)
   ```

## 🎯 One-Command Deployment

```bash
cd swarm-agents
./deploy-to-aws.sh
```

That's it! The script will:
- ✅ Check all prerequisites
- ✅ Create AWS resources (S3, DynamoDB, Key Pair)
- ✅ Deploy infrastructure with Terraform
- ✅ Verify deployment and show access URLs

## 📊 Expected Results

**Deployment Time**: 10-15 minutes

**AWS Resources Created**:
- 8 EC2 instances (auto-scaling)
- Application Load Balancer
- Aurora PostgreSQL database
- ElastiCache Redis cluster
- VPC with security groups
- S3 buckets and monitoring

**Access Points**:
- **Dashboard**: `http://<load-balancer-dns>/`
- **Grafana**: `http://<load-balancer-dns>:3000`
- **API**: `http://<load-balancer-dns>/api`

## 💰 Estimated Costs

- **First month**: ~$100-150 (with free tier)
- **Ongoing**: ~$600-800/month
- **With Reserved Instances**: ~$400-500/month

## 🛠️ Advanced Options

```bash
# Deploy to specific region
./deploy-to-aws.sh --region us-east-1

# Deploy staging environment
./deploy-to-aws.sh --environment staging

# Just create deployment plan (no changes)
./deploy-to-aws.sh --plan-only

# Check deployment status
./deploy-to-aws.sh --status

# Destroy everything (careful!)
./deploy-to-aws.sh --destroy
```

## 🔧 Customization

Edit `infrastructure/aws/terraform.tfvars` before deployment:

```hcl
# Instance sizes (cost optimization)
swarm_queen_instance_type = "t3.medium"  # Default: t3.large
swarm_agent_instance_type = "t3.micro"   # Default: t3.small

# Scaling limits
agent_min_size = 2    # Default: 3
agent_max_size = 8    # Default: 10

# Database settings
db_instance_class = "db.t3.small"  # Default: db.t3.medium
```

## 🚨 Troubleshooting

**Common Issues**:

1. **"Access Denied" errors**:
   ```bash
   # Verify AWS credentials
   aws sts get-caller-identity
   ```

2. **"Bucket name already exists"**:
   ```bash
   # Script auto-generates unique names, but if it fails:
   export TERRAFORM_STATE_BUCKET="your-unique-bucket-name"
   ./deploy-to-aws.sh
   ```

3. **Terraform state lock**:
   ```bash
   # If deployment was interrupted
   cd infrastructure/aws
   terraform force-unlock <lock-id>
   ```

4. **Can't access dashboard**:
   ```bash
   # Check security groups allow your IP
   # Services take 5-10 minutes to fully start
   ./deploy-to-aws.sh --status
   ```

## 🔗 Next Steps

After deployment:

1. **Access Dashboard**: Use the URL provided after deployment
2. **Configure TGE Settings**: Set up your Twitter API keys and detection parameters
3. **Monitor Performance**: Check Grafana dashboards for system health
4. **Scale as Needed**: Adjust instance counts based on usage

## 📞 Support

- **Logs**: Check CloudWatch Logs in AWS Console
- **Infrastructure**: Review Terraform outputs with `--status`
- **SSH Access**: Use the generated key pair to access instances
- **Emergency**: Use `--destroy` to clean up all resources

## 🎉 Success!

Your TGE Swarm is now running on AWS with:
- ✅ Production-grade infrastructure
- ✅ Auto-scaling and load balancing  
- ✅ Comprehensive monitoring
- ✅ Automatic backups
- ✅ Security best practices

Happy TGE hunting! 🚀