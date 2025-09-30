# Crypto TGE Monitor

A Token Generation Event (TGE) monitoring system that continuously monitors news sources and Twitter for TGE-related announcements from specific companies and sends email alerts when relevant content is detected.

## Features

- **News Monitoring**: Monitors 60+ cryptocurrency news sources via RSS feeds
- **Twitter Monitoring**: Tracks Twitter timelines and searches for TGE announcements
- **Smart Matching**: Sophisticated multi-strategy content matching with company aliases and TGE keywords
- **Email Alerts**: Rich HTML email notifications with embedded CSS styling
- **Deduplication**: Prevents duplicate alerts using persistent state management
- **Circuit Breakers**: Automatic failure handling and recovery mechanisms
- **Health Monitoring**: Comprehensive system health checks and metrics
- **Production Ready**: Systemd service, log rotation, and automated deployment

## System Status

The system monitors **19 companies** and **65+ TGE keywords** across multiple news sources and social media platforms.

## Quick Start

### Local Development

1. **Clone the repository:**
   ```bash
   git clone https://github.com/mellis-netizen/OCL_Twitter_Scraper.git
   cd OCL_Twitter_Scraper
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Run the application:**
   ```bash
   # Single monitoring cycle
   python src/main.py --mode once

   # Continuous monitoring
   python src/main.py --mode continuous

   # Test all components
   python src/main.py --mode test

   # Check system status
   python src/main.py --mode status
   ```

## AWS Deployment (EC2)

### Automated Deployment

The repository includes automated deployment via GitHub Actions:

1. **Set up GitHub Secrets:**
   - `EC2_HOST`: Your EC2 instance IP or hostname
   - `EC2_USERNAME`: SSH username (usually `ubuntu` or `ec2-user`)
   - `EC2_SSH_KEY`: Private SSH key for EC2 access
   - `EC2_PORT`: SSH port (usually `22`)

2. **Deploy to EC2:**
   ```bash
   # Push to main branch triggers automatic deployment
   git push origin main
   ```

### Manual Deployment

1. **Initial deployment:**
   ```bash
   # Copy deployment script to EC2 and run as root
   scp deploy.sh user@your-ec2-instance:~/
   ssh user@your-ec2-instance
   sudo chmod +x deploy.sh
   sudo ./deploy.sh
   ```

2. **Configure environment:**
   ```bash
   sudo nano /opt/crypto-tge-monitor/.env
   # Add your email and API credentials
   sudo systemctl restart crypto-tge-monitor
   ```

3. **Future updates:**
   ```bash
   sudo ./update.sh
   ```

## Email Configuration

### Gmail Setup (Recommended)

1. **Enable 2-Factor Authentication** in your Google Account
2. **Generate App Password:**
   - Go to Google Account Settings → Security → App Passwords
   - Generate password for "Mail"
3. **Configure environment:**
   ```env
   EMAIL_USER=your-email@gmail.com
   EMAIL_PASSWORD=your-16-character-app-password
   RECIPIENT_EMAIL=alerts@your-domain.com
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   ```

### Other Email Providers

Update SMTP settings in `.env`:
```env
# Outlook/Hotmail
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587

# Custom SMTP
SMTP_SERVER=your-smtp-server.com
SMTP_PORT=587
```

## Twitter Configuration

1. **Get Twitter Bearer Token:**
   - Apply for Twitter Developer Account
   - Create new App
   - Copy Bearer Token from App settings

2. **Configure environment:**
   ```env
   TWITTER_BEARER_TOKEN=your-bearer-token-here
   ```

3. **Disable Twitter (if not configured):**
   ```env
   DISABLE_TWITTER=1
   ```

## Repository Structure

```
crypto-tge-monitor/
├── src/                          # Application source code
│   ├── main.py                   # Main application orchestrator
│   ├── news_scraper.py           # RSS feed processing
│   ├── twitter_monitor.py        # Twitter API integration
│   ├── email_notifier.py         # Email alert system
│   └── utils.py                  # Shared utilities
├── tests/                        # Unit and integration tests
├── .github/workflows/            # GitHub Actions CI/CD
├── config.py                     # Configuration and constants
├── requirements.txt              # Python dependencies
├── deploy.sh                     # Deployment script
├── update.sh                     # Update script
├── .env.example                  # Environment template
├── CLAUDE.md                     # Development documentation
└── README.md                     # This file
```

## Configuration

### Companies Monitored

The system monitors 19 companies including:
- Corn, Curvance, Darkbright, Fabric
- Caldera, Open Eden, XAI, Espresso
- Clique, TreasureDAO, Camelot, DuckChain
- Spacecoin, FhenixToken, USD.ai, Huddle01
- Succinct, and more...

### TGE Keywords

65+ keywords including:
- Core terms: TGE, token generation event, token launch
- Launch terms: mainnet launch, protocol launch, going live
- Distribution: airdrop, token sale, ICO, IDO
- Context words: announce, release, coming soon

### News Sources

60+ cryptocurrency news sources including:
- General crypto: Decrypt, CoinDesk, The Block, Defiant
- DeFi focused: Bankless, CryptoBriefing
- Network blogs: Ethereum, Arbitrum, Avalanche

## Monitoring Modes

- **`once`**: Single monitoring cycle (good for testing)
- **`continuous`**: Runs once daily at 9 AM UTC (production mode)
- **`test`**: Tests all components individually
- **`status`**: Shows current system health and statistics

## System Management

### Service Commands (Production)
```bash
# Check status
sudo systemctl status crypto-tge-monitor

# View logs
sudo journalctl -u crypto-tge-monitor -f

# Restart service
sudo systemctl restart crypto-tge-monitor

# Stop/start service
sudo systemctl stop crypto-tge-monitor
sudo systemctl start crypto-tge-monitor
```

### Log Files
- **Application logs**: `/var/log/crypto-tge-monitor/crypto_monitor.log`
- **System logs**: `journalctl -u crypto-tge-monitor`
- **Log rotation**: Automatic daily rotation, 30 days retention

## Troubleshooting

### Common Issues

1. **Email not sending:**
   ```bash
   # Check SMTP settings
   python src/main.py --mode test
   # Check logs for SMTP errors
   tail -f logs/crypto_monitor.log
   ```

2. **Twitter rate limiting:**
   ```bash
   # Disable Twitter temporarily
   export DISABLE_TWITTER=1
   python src/main.py --mode once
   ```

3. **Service won't start:**
   ```bash
   # Check service logs
   sudo journalctl -u crypto-tge-monitor -n 50
   # Check environment file
   sudo cat /opt/crypto-tge-monitor/.env
   ```

### Health Checks

The system includes comprehensive health monitoring:
- Component initialization status
- Feed availability and response times
- API rate limit status
- Memory and performance metrics

## Development

### Adding New Companies

Edit `config.py`:
```python
COMPANIES = [
    {"name": "NewCompany", "aliases": ["New Company", "NewCo"]},
    # ... existing companies
]
```

### Adding New Keywords

Edit `config.py`:
```python
TGE_KEYWORDS = [
    "new-tge-keyword",
    # ... existing keywords
]
```

### Adding News Sources

Edit `config.py`:
```python
NEWS_SOURCES = [
    "https://new-source.com/rss.xml",
    # ... existing sources
]
```

## Performance

- **Memory usage**: ~120MB typical, ~200MB peak
- **CPU usage**: Minimal (< 5% during cycles)
- **Network**: ~10-50MB per cycle depending on feed sizes
- **Cycle time**: 60-90 seconds average per monitoring cycle
- **Response time**: Email alerts sent within 2-5 minutes of detection

## Security

- Input sanitization for all email content
- HTML entity escaping to prevent XSS
- Secure credential storage via environment variables
- Systemd security restrictions (NoNewPrivileges, PrivateTmp, etc.)
- Log rotation to prevent disk space issues

## License

This project is open source under the MIT license. Do as you will. 

## 🤝 Support

For issues, questions, or feature requests:
1. Check the troubleshooting section above
2. Review logs for error messages
3. Open an issue in this repository

## Monitoring Dashboard

Access system status anytime:
```bash
python src/main.py --mode status
```

This shows:
- Service health status
- Processing statistics
- Component diagnostics
- Performance metrics
- Alert history