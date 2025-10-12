import os
import logging
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration validation
def validate_config() -> Dict[str, bool]:
    """Validate configuration and return status of each component."""
    validation_results = {
        'email_config': False,
        'twitter_config': False,
        'logging_config': False,
        'companies_config': False,
        'sources_config': False,
        'keywords_config': False,
        'urls_config': False
    }
    
    # Validate email configuration
    try:
        email_required = ['EMAIL_USER', 'EMAIL_PASSWORD', 'RECIPIENT_EMAIL']
        email_optional = ['SMTP_SERVER', 'SMTP_PORT']
        
        # Check required fields
        if all(os.getenv(field) for field in email_required):
            validation_results['email_config'] = True
        else:
            logging.warning("Email configuration incomplete - some required fields missing")
    except Exception as e:
        logging.error(f"Email configuration validation failed: {str(e)}")
    
    # Validate Twitter configuration (Bearer token only for API v2)
    try:
        bearer_token = os.getenv('TWITTER_BEARER_TOKEN')

        # Twitter is optional, but if bearer token is provided, validate it
        if bearer_token:
            # Basic validation for bearer token format
            if len(bearer_token.strip()) >= 40 and not any(placeholder in bearer_token.lower()
                                                          for placeholder in ['your_bearer_token', 'placeholder', 'test', 'example']):
                validation_results['twitter_config'] = True
            else:
                logging.warning("Twitter bearer token appears to be invalid")
                validation_results['twitter_config'] = False
        else:
            validation_results['twitter_config'] = True  # No Twitter config is valid
    except Exception as e:
        logging.error(f"Twitter configuration validation failed: {str(e)}")
    
    # Validate logging configuration
    try:
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if log_level.upper() in valid_levels:
            validation_results['logging_config'] = True
        else:
            logging.warning(f"Invalid log level: {log_level}")
    except Exception as e:
        logging.error(f"Logging configuration validation failed: {str(e)}")
    
    # Validate companies configuration
    try:
        if COMPANIES and len(COMPANIES) > 0:
            validation_results['companies_config'] = True
        else:
            logging.warning("No companies configured for monitoring")
    except Exception as e:
        logging.error(f"Companies configuration validation failed: {str(e)}")
    
    # Validate sources configuration
    try:
        if NEWS_SOURCES and len(NEWS_SOURCES) > 0:
            validation_results['sources_config'] = True
        else:
            logging.warning("No news sources configured for monitoring")
    except Exception as e:
        logging.error(f"Sources configuration validation failed: {str(e)}")
    
    # Validate keywords configuration
    try:
        if TGE_KEYWORDS and len(TGE_KEYWORDS) > 0:
            # Check for empty or invalid keywords
            valid_keywords = [k for k in TGE_KEYWORDS if k and isinstance(k, str) and len(k.strip()) > 0]
            if len(valid_keywords) == len(TGE_KEYWORDS):
                validation_results['keywords_config'] = True
            else:
                logging.warning("Some TGE keywords are invalid or empty")
        else:
            logging.warning("No TGE keywords configured")
    except Exception as e:
        logging.error(f"Keywords configuration validation failed: {str(e)}")
    
    # Validate URLs configuration
    try:
        from urllib.parse import urlparse
        valid_urls = 0
        for url in NEWS_SOURCES:
            try:
                parsed = urlparse(url)
                if parsed.scheme in ['http', 'https'] and parsed.netloc:
                    valid_urls += 1
            except Exception:
                logging.warning(f"Invalid URL in sources: {url}")
        
        if valid_urls > 0:
            validation_results['urls_config'] = True
            logging.info(f"Validated {valid_urls}/{len(NEWS_SOURCES)} news source URLs")
        else:
            logging.error("No valid URLs found in news sources")
    except Exception as e:
        logging.error(f"URL validation failed: {str(e)}")
    
    return validation_results

# Companies to monitor - optimized for TGE detection with research-based configurations
# Priority levels: HIGH = likely to have TGE soon, MEDIUM = established but may announce new tokens, LOW = monitoring only
COMPANIES = [
    # HIGH PRIORITY - Active development, no token yet
    {"name": "Curvance", "aliases": ["Curvance Finance", "Curvance Protocol"], "tokens": ["CRV", "CURV"], "exclusions": [], "priority": "HIGH", "status": "pre_token"},
    {"name": "Fhenix", "aliases": ["Fhenix Protocol", "Fhenix Labs"], "tokens": ["FHE"], "exclusions": [], "priority": "HIGH", "status": "pre_token"},
    {"name": "Succinct", "aliases": ["Succinct Labs", "Succinct Protocol"], "tokens": ["SP1", "SUC"], "exclusions": ["succinct definition", "succinct writing"], "priority": "HIGH", "status": "pre_token"},
    {"name": "Caldera", "aliases": ["Caldera Labs", "Caldera Protocol", "Caldera Chain"], "tokens": ["CAL"], "exclusions": ["volcanic caldera", "yellowstone caldera", "caldera formation", "volcanic activity", "eruption", "volcano", "magma", "lava", "geological"], "priority": "HIGH", "status": "pre_token"},
    {"name": "Fabric", "aliases": ["Fabric Protocol", "Fabric Labs", "Fabric Cryptography"], "tokens": ["FAB"], "exclusions": ["fabric softener", "textile fabric", "fabric store", "fabric material", "cotton fabric", "silk fabric", "fabric pattern", "sewing fabric", "quilting fabric", "fabric texture", "fashion fabric"], "priority": "HIGH", "status": "pre_token"},

    # MEDIUM PRIORITY - Established projects that may launch additional tokens
    {"name": "TreasureDAO", "aliases": ["Treasure DAO", "Treasure", "Treasure Protocol"], "tokens": ["MAGIC"], "exclusions": ["treasure hunt", "national treasure", "treasure map", "hidden treasure", "treasure chest", "gold treasure", "ancient treasure", "lost treasure"], "priority": "MEDIUM", "status": "has_token"},
    {"name": "Camelot", "aliases": ["Camelot DEX", "Camelot Protocol"], "tokens": ["GRAIL"], "exclusions": ["king arthur", "camelot movie", "camelot musical", "knights of the round table"], "priority": "MEDIUM", "status": "has_token"},
    {"name": "XAI", "aliases": ["Xai Games", "Xai", "XAI Games"], "tokens": ["XAI"], "exclusions": ["explainable ai", "xai technology", "explainability", "interpretable ai"], "priority": "MEDIUM", "status": "has_token"},
    {"name": "Huddle01", "aliases": ["Huddle 01", "Huddle01 Protocol"], "tokens": ["HUD01", "HUDDLE"], "exclusions": ["football huddle", "team huddle", "sports huddle"], "priority": "MEDIUM", "status": "pre_token"},

    # LOWER PRIORITY - Less clear token plans or stablecoins
    {"name": "Open Eden", "aliases": ["OpenEden", "Open Eden Protocol"], "tokens": ["TBILL"], "exclusions": [], "priority": "LOW", "status": "has_token"},
    {"name": "USD.ai", "aliases": ["USDai", "USD AI", "USD.ai Protocol"], "tokens": ["USDAI"], "exclusions": [], "priority": "LOW", "status": "stablecoin"},
    {"name": "Espresso", "aliases": ["Espresso Systems", "Espresso Labs"], "tokens": ["ESPR"], "exclusions": ["coffee", "espresso machine", "starbucks", "espresso shot", "coffee beans", "brew", "caffeine", "coffee shop", "latte", "cappuccino", "macchiato"], "priority": "LOW", "status": "infrastructure"},

    # EXPERIMENTAL - Less certain companies, monitoring for activity
    {"name": "DuckChain", "aliases": ["Duck Chain", "DuckChain Protocol"], "tokens": ["DUCK"], "exclusions": ["rubber duck", "donald duck", "ducks", "waterfowl"], "priority": "LOW", "status": "experimental"},
    {"name": "Spacecoin", "aliases": ["Space Coin", "Spacecoin Protocol"], "tokens": ["SPACE"], "exclusions": ["nasa", "space exploration", "outer space", "spacex", "space travel"], "priority": "LOW", "status": "experimental"},
    {"name": "Clique", "aliases": ["Clique Protocol", "Clique Labs"], "tokens": ["CLI"], "exclusions": ["social clique", "clique theory", "friendship clique", "popular clique"], "priority": "LOW", "status": "experimental"}
]

# TGE-related keywords - categorized by confidence level
# High confidence keywords (strong TGE indicators) - optimized for 2024/2025 terminology
HIGH_CONFIDENCE_TGE_KEYWORDS = [
    # Core TGE terminology
    "TGE", "token generation event", "token launch", "token release",
    "token distribution", "token deployment", "token goes live",
    "token is now live", "token is live", "tokens are now available",
    
    # Modern launch terminology
    "airdrop", "airdrop is live", "claim airdrop", "airdrop campaign",
    "token sale", "IDO", "initial dex offering", "IEO", "initial exchange offering",
    "token listing", "token trading", "trading goes live", "trading is now live",
    "mainnet token", "governance token launch", "utility token launch",
    
    # Specific announcement patterns
    "announcing.*token", "excited to announce.*token", "proud to announce.*token",
    "token launch date", "token coming soon", "token dropping",
    "claim your.*token", "eligible for.*airdrop", "airdrop live",
    "token.*available.*exchange", "token.*listed.*exchange",
    "token.*trading.*enabled", "token.*trading.*live",
    
    # Distribution and claim patterns
    "token claim", "claim portal", "claiming is live", "distribution event",
    "token unlock schedule", "vesting schedule released",
    "tokenomics revealed", "token allocation",

    # NEW: Live action phrases (HIGH PRECISION)
    "token claim live", "claiming portal open", "claim window open",
    "claim page live", "distribution begins", "tokens available now",
    "claim your tokens now", "claiming starts today", "claiming starts now",
    "claim period open", "distribution live", "token distribution live",
    "distribution event started", "check if you're eligible", "eligible to claim",

    # NEW: Completion signals (HIGH PRECISION)
    "token generation complete", "mainnet token deployed", "token contract deployed",
    "genesis block mined", "network is live", "token now available",
    "contract verified", "token successfully deployed",

    # NEW: Snapshot and eligibility (HIGH PRECISION)
    "airdrop snapshot taken", "eligibility snapshot", "snapshot completed",
    "check eligibility", "snapshot complete", "eligibility check live",
    "airdrop eligibility", "qualified for airdrop",

    # NEW: Participation events (HIGH PRECISION)
    "whitelist live", "public sale begins", "token sale round",
    "contribution period open", "fundraising live", "sale starts now",
    "public sale live", "whitelist open", "registration open",

    # NEW: Community and retroactive (HIGH PRECISION)
    "community airdrop", "retroactive distribution", "user rewards distribution",
    "ecosystem airdrop", "retroactive airdrop", "community rewards",
    "loyalty airdrop", "early adopter airdrop"
]

# Medium confidence keywords (require company context) - contextual TGE signals
MEDIUM_CONFIDENCE_TGE_KEYWORDS = [
    # Launch terminology that often precedes TGE
    "mainnet launch", "mainnet deployment", "protocol launch",
    "network launch", "platform launch", "chain launch",
    "mainnet is live", "deployed to mainnet", "mainnet release",
    
    # Token-related but needs context
    "tokenomics", "token economics", "token model",
    "token unlock", "token vesting", "token emission",
    "governance token", "utility token", "native token",
    "token metrics", "token supply", "circulating supply",
    
    # Action words requiring company context
    "launching soon", "going live", "live on mainnet",
    "beta launch", "public launch", "official launch",
    "genesis event", "network genesis", "chain genesis",
    
    # Exchange and trading related
    "exchange listing", "dex listing", "cex listing",
    "liquidity pool", "LP tokens", "trading pair",
    "market making", "liquidity provision",

    # NEW: Vesting and unlock events
    "vesting begins", "token unlock event", "cliff period ends",
    "linear vesting starts", "unlock schedule", "vesting schedule",

    # NEW: Staking and rewards
    "staking live", "stake to earn", "staking rewards begin",
    "validator rewards", "staking portal open", "staking enabled",

    # NEW: Governance activation
    "governance live", "voting begins", "DAO launch",
    "proposal system live", "governance portal",

    # NEW: L2/Rollup specific
    "rollup token", "L2 token launch", "sequencer token",
    "rollup mainnet", "L2 mainnet",

    # NEW: Migration and bridge
    "token migration", "contract migration", "token swap event",
    "bridge live", "cross-chain launch"
]

# Low confidence keywords (require company + multiple strong indicators)
LOW_CONFIDENCE_TGE_KEYWORDS = [
    # Generic announcement terms
    "announce", "announced", "announcing", "announcement",
    "introducing", "excited to share", "big news",
    "major update", "important update", "milestone",

    # Timing indicators
    "coming soon", "launch date", "release date", "go live",
    "next week", "this month", "Q1", "Q2", "Q3", "Q4",
    "roadmap update", "timeline", "schedule",
    "this week", "next month", "this year",

    # Platform/exchange related
    "available on", "trading on", "listed on", "live on",
    "integrated with", "deployed on", "partnership with",
    "supported by", "launching on", "coming to"
]

# Critical exclusion patterns - to reduce false positives
EXCLUSION_PATTERNS = [
    # Gaming/NFT false positives
    "game token", "in-game token", "nft drop", "nft collection",
    "play to earn", "gaming rewards", "achievement token",
    "loot drop", "item drop", "reward drop", "battle pass",
    "season pass", "cosmetic drop", "skin drop",
    "in-app purchase", "game currency", "premium currency",
    "unlock achievement", "level up reward",
    "gacha", "loot box", "treasure chest",

    # Technical/Development false positives
    "test token", "testnet", "devnet", "staging",
    "mock token", "demo token", "example token",

    # General crypto news false positives
    "bitcoin", "ethereum", "btc", "eth", "stable coin",
    "wrapped token", "bridge token", "pegged token",

    # Opinion/Analysis false positives
    "token analysis", "token review", "token prediction",
    "price prediction", "market analysis", "technical analysis",
    "my take on", "opinion piece", "analysis of",
    "what if", "could be", "might be", "speculation",
    "rumor", "unconfirmed", "allegedly",
    "hope", "wish", "want to see",
    "prediction for", "forecast", "outlook",

    # Historical/Retrospective content
    "recap of", "looking back", "anniversary of",
    "history of", "evolution of", "timeline of",
    "flashback", "throwback", "remember when",
    "previous", "former", "old", "past",
    "archived", "historical", "legacy",
    "last year", "in 2023", "in 2022",

    # Tutorial/Educational content
    "how to claim", "guide to", "tutorial", "walkthrough",
    "explained", "breakdown", "deep dive",
    "learn about", "understanding", "what is",
    "beginner's guide", "introduction to",
    "on sale", "best deals", "sale this week",
    "for sale", "buy now", "purchase",

    # Company name false positives (from company exclusions - for comprehensive filtering)
    "fabric softener", "espresso machine", "coffee shop",
    "volcanic caldera", "treasure hunt",

    # Scam/Phishing patterns
    "free airdrop", "guaranteed airdrop", "get free tokens",
    "double your", "send to receive", "giveaway",
    "limited time offer", "act now", "don't miss out"
]

# Combined list for backward compatibility
TGE_KEYWORDS = HIGH_CONFIDENCE_TGE_KEYWORDS + MEDIUM_CONFIDENCE_TGE_KEYWORDS + LOW_CONFIDENCE_TGE_KEYWORDS

# Optimized news sources - prioritized for TGE announcement coverage
NEWS_SOURCES = [
    # TIER 1: Primary sources for TGE announcements and early-stage project coverage
    "https://www.theblock.co/rss.xml",        # The Block - excellent for major announcements
    "https://decrypt.co/feed",                # Decrypt - good DeFi/Web3 coverage
    "https://www.coindesk.com/arc/outboundfeeds/rss",  # CoinDesk - industry standard
    "https://thedefiant.io/feed",             # The Defiant - DeFi focused
    "https://www.bankless.com/feed",          # Bankless - ecosystem coverage
    "https://www.dlnews.com/arc/outboundfeeds/rss/",  # DL News - quality reporting

    # TIER 2: Secondary sources for broader coverage
    "https://cointelegraph.com/rss",          # Cointelegraph - broad coverage
    "https://cryptobriefing.com/feed",        # CryptoBriefing - analysis focused
    "https://blockonomi.com/feed/",           # Blockonomi - project coverage
    "https://bitcoinethereumnews.com/feed/",  # Bitcoin Ethereum News - altcoin focus

    # TIER 3: Specialized and ecosystem sources
    "https://u.today/rss.php",               # U.Today - good altcoin coverage
    "https://ambcrypto.com/feed/",           # AMBCrypto - analysis
    "https://dailycoin.com/feed/",           # DailyCoin - project news
    "https://cryptopotato.com/feed/",        # CryptoPotato - broad coverage
    "https://crypto.news/feed/",             # Crypto.news - timely updates
    "https://www.trustnodes.com/feed",      # Trustnodes - technical focus
    "https://multicoin.capital/rss.xml",    # Multicoin - VC perspective on projects

    # TIER 4: Network ecosystem blogs for protocol-level announcements
    "https://blog.ethereum.org/en/feed.xml",              # Ethereum Foundation
    "https://arbitrumfoundation.medium.com/feed",         # Arbitrum Foundation
    "https://medium.com/feed/@AstarNetwork",              # Astar Network
    "https://blog.polygon.technology/feed/",              # Polygon blog (if available)
]
# Optimized Twitter monitoring - focus on companies with active accounts and TGE potential
COMPANY_TWITTERS = {
    # HIGH PRIORITY - Active companies likely to announce TGE
    "Curvance": "@CurvanceFinance",     # Pre-token, active development
    "Fhenix": "@FhenixIO",              # Pre-token, FHE protocol
    "Succinct": "@SuccinctLabs",        # Pre-token, ZK infrastructure
    "Caldera": "@CalderaXYZ",           # Pre-token, rollup platform
    "Fabric": "@fabric_xyz",            # Pre-token, cryptography

    # MEDIUM PRIORITY - Established with potential for new tokens/updates
    "TreasureDAO": "@Treasure_DAO",     # Has MAGIC, may launch additional tokens
    "Camelot": "@CamelotDEX",          # Has GRAIL, DEX with expansion potential
    "XAI": "@XaiGames",                # Gaming, established but growing
    "Huddle01": "@huddle01",           # Pre-token, Web3 communication

    # LOWER PRIORITY - Less likely to have immediate TGE
    "Open Eden": "@OpenEden_HQ",       # Has TBILL, stablecoin focus
    "Espresso": "@EspressoSys",        # Infrastructure, unclear token plans
}

# Optimized Twitter news monitoring - focused on TGE announcement coverage
CORE_NEWS_TWITTERS = [
    # TIER 1: Primary news sources for TGE announcements
    "@TheBlock__",          # The Block - excellent for major announcements
    "@decryptmedia",        # Decrypt - good DeFi/Web3 coverage
    "@CoinDesk",            # CoinDesk - industry standard
    "@DefiantNews",         # The Defiant - DeFi focused
    "@BanklessHQ",          # Bankless - ecosystem coverage
    "@DLNewsInfo",          # DL News - quality reporting

    # TIER 2: Influential voices and analysis
    "@MessariCrypto",       # Messari - research and analysis
    "@WuBlockchain",        # Wu Blockchain - breaking news
    "@Delphi_Digital",      # Delphi Digital - research firm
    "@multicoincap",        # Multicoin Capital - VC perspective
    "@a16zcrypto",          # a16z crypto - major VC fund

    # TIER 3: Project discovery and early coverage
    "@CoinList",            # CoinList - token launch platform
    "@WatcherGuru",         # Watcher Guru - news aggregation
    "@Foresight_News",      # Foresight News - Asian coverage
    "@Cointelegraph",       # Cointelegraph - broad coverage
    "@Blockworks_",         # Blockworks - institutional focus

    # TIER 4: Key ecosystem and thought leaders (selective)
    "@VitalikButerin",      # Ethereum founder - may comment on projects
    "@DefiLlama",           # DeFi Llama - analytics, often covers new projects
    "@ethereum",            # Ethereum Foundation
    "@arbitrum",            # Arbitrum - Layer 2 ecosystem
    "@0xPolygon",           # Polygon - ecosystem projects
    "@OffchainLabs",        # Offchain Labs - Arbitrum team

     # DeFi and Web3 influencers
    "@PatrickAlphaC",
    "@VittoStack",
    "@thatguyintech",
    "@iam_preethi",
    "@dabit3",
    "@oliverjumpertz",
    "@austingriffith",
    "@sandeepnailwal",
    "@el33th4xor",
    "@michaelfkong",
    "@kelvinfichter",
]

# Derived list of Twitter accounts to monitor
TWITTER_ACCOUNTS = [
    handle for handle in (
        list({h for h in COMPANY_TWITTERS.values() if h}) + CORE_NEWS_TWITTERS
    )
]

# Email configuration
EMAIL_CONFIG = {
    'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
    'smtp_port': int(os.getenv('SMTP_PORT', 587)),
    'email_user': os.getenv('EMAIL_USER'),
    'email_password': os.getenv('EMAIL_PASSWORD'),
    'recipient_email': os.getenv('RECIPIENT_EMAIL', 'mellis@offchainlabs.com')
}

# Twitter API configuration (Bearer token only for API v2)
TWITTER_CONFIG = {
    'bearer_token': os.getenv('TWITTER_BEARER_TOKEN')
}

# Logging configuration
LOG_CONFIG = {
    'level': os.getenv('LOG_LEVEL', 'INFO'),
    'file': os.getenv('LOG_FILE', 'logs/crypto_monitor.log')
}

# Swarm coordination configuration
SWARM_CONFIG = {
    'enabled': os.getenv('SWARM_ENABLED', 'false').lower() == 'true',
    'session_id': os.getenv('SWARM_SESSION_ID', None),
    'agent_id': os.getenv('SWARM_AGENT_ID', 'main-scraper'),
    'agent_role': os.getenv('SWARM_AGENT_ROLE', 'scraping-efficiency-specialist'),
    'coordination_enabled': os.getenv('SWARM_COORDINATION_ENABLED', 'true').lower() == 'true',
    'memory_enabled': os.getenv('SWARM_MEMORY_ENABLED', 'true').lower() == 'true',
    'rate_limit_coordination': os.getenv('SWARM_RATE_LIMIT_COORD', 'true').lower() == 'true',
    'dedup_coordination': os.getenv('SWARM_DEDUP_COORD', 'true').lower() == 'true',
}

# Swarm agent definitions (matching safla-swarm-config.yaml)
SWARM_AGENTS = {
    'scraping-efficiency-specialist': {
        'role': 'primary-optimizer',
        'priority': 'critical',
        'focus': [
            'scraper-performance-tuning',
            'api-rate-limit-optimization',
            'concurrent-request-efficiency',
            'cache-strategy-optimization'
        ],
        'files': [
            'src/news_scraper*.py',
            'src/twitter_monitor*.py',
            'src/main*.py'
        ]
    },
    'tge-keyword-precision-specialist': {
        'role': 'accuracy-optimizer',
        'priority': 'critical',
        'focus': [
            'keyword-matching-precision',
            'false-positive-elimination',
            'company-name-matching-accuracy',
            'context-aware-filtering'
        ],
        'files': [
            'config.py',
            'src/news_scraper*.py',
            'src/main*.py'
        ]
    },
    'api-reliability-optimizer': {
        'role': 'integration-hardener',
        'priority': 'high',
        'focus': [
            'error-handling-robustness',
            'retry-mechanism-optimization',
            'circuit-breaker-implementation',
            'rate-limit-intelligent-backoff'
        ],
        'files': [
            'src/twitter_monitor*.py',
            'src/news_scraper*.py',
            'src/health_endpoint.py'
        ]
    }
}

