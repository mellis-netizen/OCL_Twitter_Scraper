# 🔑 How to Get Your AWS Key Name - Step by Step Guide

The "your-aws-key-name" is an SSH key pair that you need to create in AWS to securely connect to your EC2 instance. Here's exactly how to get it:

## 🎯 What You Need

An **SSH Key Pair** consists of:
- **Private Key** (stays on your computer)
- **Public Key** (stored in AWS)

This allows secure SSH access to your EC2 instance.

---

## 📋 Method 1: Create Key via AWS Console (Easiest)

### Step 1: Log into AWS Console
1. Go to [AWS Console](https://console.aws.amazon.com/)
2. Log in with your AWS credentials
3. Navigate to **EC2** service

### Step 2: Create Key Pair
1. In the EC2 Dashboard, click **"Key Pairs"** in the left sidebar
2. Click **"Create key pair"** button
3. Fill in the details:
   ```
   Name: tge-monitor-key
   Key pair type: RSA
   Private key file format: .pem
   ```
4. Click **"Create key pair"**

### Step 3: Download and Secure
1. Your browser will automatically download `tge-monitor-key.pem`
2. Move it to your SSH directory:
   ```bash
   mv ~/Downloads/tge-monitor-key.pem ~/.ssh/
   chmod 400 ~/.ssh/tge-monitor-key.pem
   ```

### Step 4: Use in Deployment
Your key name is: **`tge-monitor-key`**

```bash
./deploy-complete.sh tge-monitor-key us-east-1
```

---

## 📋 Method 2: Create Key via AWS CLI

### Step 1: Create Key Pair
```bash
aws ec2 create-key-pair \
    --key-name tge-monitor-key \
    --query 'KeyMaterial' \
    --output text > ~/.ssh/tge-monitor-key.pem
```

### Step 2: Set Permissions
```bash
chmod 400 ~/.ssh/tge-monitor-key.pem
```

### Step 3: Verify Creation
```bash
aws ec2 describe-key-pairs --key-names tge-monitor-key
```

### Step 4: Use in Deployment
```bash
./deploy-complete.sh tge-monitor-key us-east-1
```

---

## 📋 Method 3: Use Existing Key

### If You Already Have a Key Pair:

1. **List existing keys:**
   ```bash
   aws ec2 describe-key-pairs
   ```

2. **Find your key name** in the output (look for "KeyName")

3. **Use that name:**
   ```bash
   ./deploy-complete.sh your-existing-key-name us-east-1
   ```

---

## 🔍 Complete Example Walkthrough

Let's say you want to create a key called `my-tge-key`:

### Step 1: Create the Key
```bash
aws ec2 create-key-pair \
    --key-name my-tge-key \
    --query 'KeyMaterial' \
    --output text > ~/.ssh/my-tge-key.pem
```

### Step 2: Secure the Key
```bash
chmod 400 ~/.ssh/my-tge-key.pem
```

### Step 3: Deploy with Your Key
```bash
./deploy-complete.sh my-tge-key us-east-1
```

### Step 4: Access Your Instance Later
```bash
ssh -i ~/.ssh/my-tge-key.pem ubuntu@your-instance-ip
```

---

## 🌍 Different Regions

The key pair is **region-specific**. Create keys in the region where you want to deploy:

### US East (Virginia) - Most Common
```bash
aws ec2 create-key-pair --region us-east-1 --key-name my-key
./deploy-complete.sh my-key us-east-1
```

### US West (California)
```bash
aws ec2 create-key-pair --region us-west-1 --key-name my-key
./deploy-complete.sh my-key us-west-1
```

### Europe (Ireland)
```bash
aws ec2 create-key-pair --region eu-west-1 --key-name my-key
./deploy-complete.sh my-key eu-west-1
```

---

## ❌ Troubleshooting

### Problem: "Key pair 'xxx' does not exist"
**Solution:** Create the key pair first:
```bash
aws ec2 create-key-pair --key-name xxx --query 'KeyMaterial' --output text > ~/.ssh/xxx.pem
chmod 400 ~/.ssh/xxx.pem
```

### Problem: "Permission denied (publickey)"
**Solution:** Check key permissions:
```bash
chmod 400 ~/.ssh/your-key.pem
```

### Problem: "Key pair already exists"
**Solution:** Either use existing key or create with different name:
```bash
aws ec2 create-key-pair --key-name my-new-unique-key-name
```

### Problem: "Wrong region"
**Solution:** Create key in the correct region:
```bash
aws ec2 create-key-pair --region us-east-1 --key-name my-key
```

---

## 🔐 Security Best Practices

### 1. Secure Your Private Key
```bash
# Move to secure location
mv ~/Downloads/your-key.pem ~/.ssh/
# Set restrictive permissions
chmod 400 ~/.ssh/your-key.pem
# Never share this file!
```

### 2. Use Descriptive Names
```bash
# Good names
tge-monitor-production-key
my-company-dev-key
project-staging-key

# Avoid
key1
test
mykey
```

### 3. Backup Your Keys
```bash
# Create backup
cp ~/.ssh/your-key.pem ~/.ssh/backups/your-key-backup.pem
```

### 4. Delete Unused Keys
```bash
# List keys
aws ec2 describe-key-pairs

# Delete unused key
aws ec2 delete-key-pair --key-name old-unused-key
```

---

## ✅ Quick Setup Commands

### Complete Setup in 3 Commands:
```bash
# 1. Create key
aws ec2 create-key-pair --key-name tge-key --query 'KeyMaterial' --output text > ~/.ssh/tge-key.pem

# 2. Secure key
chmod 400 ~/.ssh/tge-key.pem

# 3. Deploy system
./deploy-complete.sh tge-key us-east-1
```

That's it! Your TGE Monitor system will be deployed and ready to use.

---

## 🎯 Summary

**Your AWS key name is simply the name you give to your SSH key pair when creating it.**

Common examples:
- `tge-monitor-key`
- `my-production-key`
- `company-dev-key`

The deployment script needs this name to:
1. Launch an EC2 instance with your key
2. Connect to the instance via SSH
3. Deploy the TGE Monitor system

**Next Step:** Create your key using one of the methods above, then run:
```bash
./deploy-complete.sh YOUR-KEY-NAME us-east-1
```