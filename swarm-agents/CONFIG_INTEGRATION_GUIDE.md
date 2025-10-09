# TGE Swarm config.py Integration Guide

This guide explains how the root `config.py` file is integrated into both AWS deployment versions of the TGE Swarm system.

## 📋 Overview

The `config.py` file from the root directory contains all the TGE monitoring configuration including:
- Company monitoring targets with priorities
- TGE-related keywords for detection
- News sources for scraping
- Twitter accounts to monitor
- Email and logging configuration

## 🔧 Integration in Both AWS Deployments

### Production AWS Deployment (`infrastructure/aws/`)

#### File Locations
```
/opt/tge-swarm/config.py                    # Original from repository
/opt/tge-swarm/swarm-agents/config.py       # Copy for swarm agents
/app/config/config.py                       # Copy for services
```

#### Environment Configuration
The production deployment creates `.env` files with:
```bash
# TGE Monitoring Configuration
LOG_LEVEL=INFO
LOG_FILE=/app/logs/tge_monitor.log

# Email Configuration (from AWS Parameter Store)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=${email_user}
EMAIL_PASSWORD=${email_password}
RECIPIENT_EMAIL=${recipient_email}

# Twitter Configuration (from AWS Parameter Store)
TWITTER_BEARER_TOKEN=${twitter_bearer_token}

# AWS Integration
AWS_REGION=${AWS::Region}
ENVIRONMENT=${environment}
```

#### Service Integration
- **Systemd Service**: `/etc/systemd/system/tge-swarm-queen.service`
  - Uses `EnvironmentFile=/app/config/.env`
  - Sets `PYTHONPATH=/opt/tge-swarm/swarm-agents:/opt/tge-swarm`
- **User Data Script**: `infrastructure/aws/user-data/swarm-queen.sh`
  - Installs `python-dotenv` dependency
  - Copies config files to all required locations
  - Sets up environment variables

### Low-Cost AWS Deployment (`lowest_possible_cost_aws/`)

#### File Locations
```
/opt/tge-swarm/config.py                    # Original from repository
/opt/tge-swarm/swarm-agents/config.py       # Copy for swarm agents
/opt/tge-swarm/config/config.py             # Copy in container
/app/config.py                              # In Docker container
```

#### Container Integration
- **Dockerfile**: `docker/Dockerfile.all-in-one`
  ```dockerfile
  COPY config.py .                          # Line 29
  COPY swarm-agents/ ./swarm-agents/        # Line 30
  ```

#### Startup Validation
- **Startup Script**: `scripts/start-all-services.sh`
  - Validates config.py on startup
  - Sets `PYTHONPATH="/app:/app/swarm-agents:$PYTHONPATH"`
  - Runs configuration validation before services start

#### Environment Configuration
```bash
# TGE Monitoring Configuration
LOG_LEVEL=INFO
LOG_FILE=/opt/tge-swarm/logs/tge_monitor.log

# AWS Integration for cost-optimized deployment
AWS_REGION=${region}
ENVIRONMENT=cost-optimized
```

## 📊 Configuration Components Used

### Companies Monitoring
The swarm agents use `config.COMPANIES` for:
- **High Priority**: Curvance, Fhenix, Succinct, Caldera, Fabric
- **Medium Priority**: TreasureDAO, Camelot, XAI, Huddle01
- **Low Priority**: Open Eden, USD.ai, Espresso

### TGE Keywords
Three tiers of keywords from `config.py`:
- **High Confidence**: "TGE", "token generation event", "airdrop", etc.
- **Medium Confidence**: "mainnet launch", "tokenomics", etc.  
- **Low Confidence**: "announcement", "coming soon", etc.

### News Sources
16 RSS feeds prioritized by TGE announcement coverage:
- **Tier 1**: The Block, Decrypt, CoinDesk, The Defiant
- **Tier 2**: Cointelegraph, CryptoBriefing, Blockonomi
- **Tier 3-4**: Specialized and ecosystem sources

### Twitter Monitoring
- **Company Accounts**: Direct monitoring of target companies
- **News Accounts**: Crypto news outlets and influencers
- **Total**: 50+ Twitter accounts for comprehensive coverage

## 🔄 Usage in Swarm Services

### Configuration Validation
Both deployments run validation on startup:
```python
import config
validation_results = config.validate_config()

# Checks:
# - email_config: Email settings validity
# - twitter_config: Bearer token format
# - companies_config: Company list completeness
# - sources_config: News sources availability
# - keywords_config: TGE keywords validity
# - urls_config: RSS feed URL validation
```

### Service Integration Points

#### 1. **TGE Queen Orchestrator**
```python
from config import COMPANIES, TGE_KEYWORDS, NEWS_SOURCES
# Uses config for coordinating detection across sources
```

#### 2. **Memory Coordinator** 
```python
from config import TWITTER_ACCOUNTS, COMPANY_TWITTERS
# Manages shared memory for cross-platform detection
```

#### 3. **Specialized Agents**
- **Scraping Efficiency Specialist**: Uses `NEWS_SOURCES` optimization
- **Keyword Precision Specialist**: Uses `TGE_KEYWORDS` refinement
- **API Reliability Optimizer**: Uses `TWITTER_CONFIG` for rate limiting
- **Performance Bottleneck Eliminator**: Uses all config for optimization
- **Data Quality Enforcer**: Uses `EXCLUSION_PATTERNS` for filtering

## 🛠️ Configuration Management

### AWS Parameter Store Integration (Production)
```bash
# Store sensitive values in Parameter Store
aws ssm put-parameter \
  --name "/tge-swarm/email-user" \
  --value "your-email@gmail.com" \
  --type "SecureString"

aws ssm put-parameter \
  --name "/tge-swarm/twitter-bearer-token" \
  --value "your-bearer-token" \
  --type "SecureString"
```

### Environment Variable Override
Both deployments support environment variable overrides:
```bash
# Override email configuration
export EMAIL_USER="custom@email.com"
export RECIPIENT_EMAIL="alerts@company.com"

# Override Twitter configuration  
export TWITTER_BEARER_TOKEN="your-token"

# Override logging
export LOG_LEVEL="DEBUG"
export LOG_FILE="/custom/path/logs.log"
```

## 🔍 Monitoring & Validation

### Startup Validation
Both deployments validate config.py on startup:
```
Configuration validation: 6/7 components valid
  email_config: INVALID (credentials not configured)
  twitter_config: VALID
  logging_config: VALID
  companies_config: VALID
  sources_config: VALID  
  keywords_config: VALID
  urls_config: VALID
```

### Runtime Usage
- **Configuration Hot-Reload**: Services monitor config changes
- **Validation Alerts**: CloudWatch alarms for configuration issues
- **Performance Tracking**: Metrics on keyword match rates
- **Source Monitoring**: RSS feed health and response times

## 🚨 Troubleshooting

### Common Issues

1. **Config Import Errors**
   ```bash
   # Check Python path
   echo $PYTHONPATH
   
   # Verify config.py location
   ls -la /opt/tge-swarm/config.py
   ls -la /app/config.py
   ```

2. **Environment Variable Issues**
   ```bash
   # Check .env file loading
   cat /app/config/.env
   
   # Verify environment in container
   docker exec container-name env | grep -E "(EMAIL|TWITTER|LOG)"
   ```

3. **Validation Failures**
   ```bash
   # Test configuration manually
   python -c "import config; print(config.validate_config())"
   
   # Check specific components
   python -c "import config; print(len(config.COMPANIES))"
   python -c "import config; print(len(config.TGE_KEYWORDS))"
   ```

### Health Checks
Both deployments include config validation in health checks:
```bash
# Production
curl http://load-balancer/health/config

# Low-cost  
curl http://localhost:8080/health/config
```

## 📈 Performance Impact

### Memory Usage
- **config.py Loading**: ~2MB (companies, keywords, sources)
- **Runtime Caching**: ~5MB (compiled patterns, validated URLs)
- **Total Impact**: <1% of container memory

### Startup Time
- **Config Validation**: ~2-3 seconds
- **Environment Setup**: ~1-2 seconds  
- **Total Addition**: ~5 seconds to startup

### Resource Optimization
- **Lazy Loading**: Only load needed config sections
- **Caching**: Cache compiled regex patterns
- **Validation**: Skip expensive checks in production

This integration ensures that both AWS deployment versions use the same authoritative TGE monitoring configuration while optimizing for their respective cost and performance requirements.