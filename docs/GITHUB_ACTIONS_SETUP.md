# GitHub Actions Setup Guide

This guide explains how to configure GitHub Secrets for the TGE Swarm Agent Monitoring workflow.

## 📋 Overview

The project includes two main GitHub Actions workflows:
1. **`swarm-agent-monitoring.yml`** - Runs TGE monitoring with swarm agents
2. **`deploy.yml`** - Deploys to EC2 production server

## 🔐 Required GitHub Secrets

### For TGE Swarm Monitoring (`swarm-agent-monitoring.yml`)

Navigate to your repository **Settings → Secrets and variables → Actions → New repository secret**

#### Email Configuration (Required)

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `SMTP_SERVER` | SMTP server address | `smtp.maileroo.com` |
| `SMTP_PORT` | SMTP port number | `587` |
| `EMAIL_USER` | Email username/address | `your-email@domain.com` |
| `EMAIL_PASSWORD` | Email password or app-specific password | `your-password-here` |
| `RECIPIENT_EMAIL` | Alert recipient email | `alerts@yourdomain.com` |

#### Twitter API Credentials (Required)

Get these from [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)

| Secret Name | Description | How to Get |
|-------------|-------------|------------|
| `TWITTER_API_KEY` | Twitter API Key | Developer Portal → Project → Keys and tokens → API Key |
| `TWITTER_API_SECRET` | Twitter API Secret | Developer Portal → Project → Keys and tokens → API Secret Key |
| `TWITTER_ACCESS_TOKEN` | Twitter Access Token | Developer Portal → Project → Keys and tokens → Access Token |
| `TWITTER_ACCESS_TOKEN_SECRET` | Twitter Access Token Secret | Developer Portal → Project → Keys and tokens → Access Token Secret |
| `TWITTER_BEARER_TOKEN` | Twitter Bearer Token | Developer Portal → Project → Keys and tokens → Bearer Token |

#### Optional Configuration

| Secret Name | Description | Default |
|-------------|-------------|---------|
| `DB_PASSWORD` | PostgreSQL database password | `tge_password` |
| `LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | `INFO` |

### For EC2 Deployment (`deploy.yml`)

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `EC2_HOST` | EC2 instance IP or hostname | `ec2-xx-xxx-xxx-xx.compute.amazonaws.com` |
| `EC2_USERNAME` | SSH username | `ubuntu` or `ec2-user` |
| `EC2_SSH_KEY` | Private SSH key (.pem file contents) | See below |

#### How to Add EC2_SSH_KEY

1. Locate your EC2 private key file (`.pem` file)
2. Copy the **entire contents** including headers:
   ```
   -----BEGIN RSA PRIVATE KEY-----
   MIIEpAIBAAKCAQEA...
   ...
   -----END RSA PRIVATE KEY-----
   ```
3. Paste into the GitHub Secret value field
4. **Important**: Include all line breaks and formatting

## 🚀 Setting Up Secrets

### Method 1: Using GitHub Web Interface

1. Go to your repository on GitHub
2. Click **Settings** (must have admin access)
3. Navigate to **Secrets and variables → Actions**
4. Click **New repository secret**
5. Enter the secret name (exact match from tables above)
6. Paste the secret value
7. Click **Add secret**
8. Repeat for all required secrets

### Method 2: Using GitHub CLI

```bash
# Install GitHub CLI if not already installed
# macOS: brew install gh
# Linux: See https://cli.github.com/

# Login to GitHub
gh auth login

# Add secrets
gh secret set SMTP_SERVER --body "smtp.maileroo.com"
gh secret set EMAIL_USER --body "your-email@domain.com"
gh secret set EMAIL_PASSWORD --body "your-password"
gh secret set RECIPIENT_EMAIL --body "alerts@domain.com"

# Twitter API
gh secret set TWITTER_API_KEY --body "your-api-key"
gh secret set TWITTER_API_SECRET --body "your-api-secret"
gh secret set TWITTER_ACCESS_TOKEN --body "your-access-token"
gh secret set TWITTER_ACCESS_TOKEN_SECRET --body "your-access-token-secret"
gh secret set TWITTER_BEARER_TOKEN --body "your-bearer-token"

# EC2 Deployment (if using)
gh secret set EC2_HOST --body "your-ec2-host"
gh secret set EC2_USERNAME --body "ubuntu"
gh secret set EC2_SSH_KEY < /path/to/your-key.pem
```

## ✅ Verification

### Check Secrets Are Set

```bash
# List all secrets (values are hidden)
gh secret list
```

### Test the Workflow

1. **Manual Trigger** (recommended for first test):
   - Go to **Actions** tab in your repository
   - Select **TGE Swarm Agent Monitoring** workflow
   - Click **Run workflow**
   - Select branch and click **Run workflow**

2. **Monitor the Run**:
   - Click on the running workflow
   - Watch the steps execute
   - Check for any errors related to missing secrets

3. **Expected Behavior**:
   - ✅ All steps should complete without "missing secret" errors
   - ✅ Logs should show successful initialization
   - ⚠️ Some monitoring steps may show warnings (expected if no alerts found)

## 🔧 Troubleshooting

### Error: "Secret not found"

**Solution**: Double-check secret name spelling matches exactly (case-sensitive)

```bash
# Verify secret exists
gh secret list | grep SMTP_SERVER
```

### Error: "Authentication failed" for Twitter API

**Possible Causes**:
1. Invalid Twitter API credentials
2. Twitter API access level insufficient
3. Rate limits exceeded

**Solution**:
- Verify credentials in Twitter Developer Portal
- Ensure "Elevated" access is granted for your app
- Check API usage limits

### Error: "SMTP authentication failed"

**Possible Causes**:
1. Incorrect email password
2. 2FA/App-specific password required
3. SMTP server blocking connection

**Solution**:
- For Gmail: Use an [App Password](https://support.google.com/accounts/answer/185833)
- For Outlook: Use app-specific password
- Check SMTP server allows external connections

### Error: "Can't connect without a private SSH key" (EC2)

**Possible Causes**:
1. `EC2_SSH_KEY` secret not set
2. Key format incorrect
3. Missing BEGIN/END headers

**Solution**:
```bash
# Verify your key file format
cat your-key.pem

# Should start with:
# -----BEGIN RSA PRIVATE KEY-----
# Should end with:
# -----END RSA PRIVATE KEY-----

# Add the secret with proper formatting
gh secret set EC2_SSH_KEY < your-key.pem
```

### Workflow Runs But No Alerts

This is **normal** if:
- No TGE events detected in monitoring period
- Twitter API returned no relevant tweets
- Content analysis didn't find high-confidence matches

Check logs for:
```
✅ Monitoring cycle completed
```

## 📊 Monitoring Workflow Behavior

### Scheduled Runs

The workflow runs automatically:
- **Every 4 hours** via cron schedule
- Can be disabled by editing `.github/workflows/swarm-agent-monitoring.yml`

### Manual Runs

Trigger manually for testing:
- Via GitHub Actions UI (recommended)
- Via GitHub CLI: `gh workflow run swarm-agent-monitoring.yml`

### Artifacts

After each run, logs are saved as artifacts:
- Retention: 7 days
- Location: Actions → Workflow run → Artifacts
- Download and review for debugging

## 🔒 Security Best Practices

1. **Never commit secrets** to the repository
2. **Rotate credentials** regularly (every 90 days)
3. **Use least-privilege** access for API keys
4. **Monitor secret usage** in Actions logs
5. **Revoke compromised** secrets immediately

## 📝 Additional Resources

- [GitHub Actions Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Twitter API Documentation](https://developer.twitter.com/en/docs/twitter-api)
- [GitHub CLI Documentation](https://cli.github.com/manual/)

## 🆘 Getting Help

If you encounter issues:

1. **Check workflow logs**: Actions → Failed run → View logs
2. **Review secret names**: Settings → Secrets → Compare with this guide
3. **Test locally**: Use `.env` file with same values
4. **Open an issue**: Include sanitized error messages (remove secrets!)

---

**Last Updated**: 2025-10-10
**Workflow Version**: v1.0
