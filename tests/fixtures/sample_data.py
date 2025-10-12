"""
Test Fixtures and Sample Data
Provides reusable test data for TGE scraping tests
"""

import time
from datetime import datetime, timezone
from typing import Dict, List


# Sample Companies
SAMPLE_COMPANIES = [
    {
        "name": "Caldera",
        "aliases": ["Caldera Labs", "Caldera Protocol"],
        "tokens": ["CAL"],
        "priority": "HIGH",
        "status": "pre_token"
    },
    {
        "name": "Fabric",
        "aliases": ["Fabric Protocol", "Fabric Labs"],
        "tokens": ["FAB"],
        "priority": "MEDIUM",
        "status": "pre_token"
    },
    {
        "name": "Succinct",
        "aliases": ["Succinct Labs"],
        "tokens": ["SUC", "SP1"],
        "priority": "HIGH",
        "status": "pre_token"
    }
]

# Sample Keywords
SAMPLE_KEYWORDS = [
    "TGE",
    "token generation event",
    "token launch",
    "airdrop",
    "token sale",
    "token distribution"
]

# Sample RSS Feed Entries
SAMPLE_FEED_ENTRIES = [
    {
        "title": "Caldera Announces Token Generation Event",
        "link": "https://example.com/caldera-tge",
        "summary": "Caldera Labs announces their TGE scheduled for next week",
        "published_parsed": time.struct_time((2024, 1, 15, 12, 0, 0, 0, 0, 0)),
        "content": """
        Caldera Labs is excited to announce our Token Generation Event (TGE)
        scheduled for January 22, 2024. The $CAL token will be distributed to
        early supporters through an airdrop. Trading will go live on major
        decentralized exchanges immediately following the TGE.
        """
    },
    {
        "title": "Fabric Protocol Mainnet Launch",
        "link": "https://example.com/fabric-mainnet",
        "summary": "Fabric Protocol launches mainnet with new features",
        "published_parsed": time.struct_time((2024, 1, 14, 10, 30, 0, 0, 0, 0)),
        "content": """
        Fabric Protocol successfully launched its mainnet today. While the
        protocol is now live, the team has not yet announced details about
        their native token or tokenomics.
        """
    },
    {
        "title": "General Crypto Market Update",
        "link": "https://example.com/market-update",
        "summary": "Daily cryptocurrency market analysis",
        "published_parsed": time.struct_time((2024, 1, 13, 9, 0, 0, 0, 0, 0)),
        "content": """
        Bitcoin and Ethereum showed strong performance today. Market cap
        increased by 3% across major cryptocurrencies. Traders remain
        optimistic about Q1 2024.
        """
    }
]

# Sample Tweets
SAMPLE_TWEETS = [
    {
        "id": "1234567890",
        "text": "Caldera TGE is live! Claim your $CAL tokens now at claim.caldera.xyz",
        "author_id": "caldera_official",
        "created_at": datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc),
        "public_metrics": {
            "retweet_count": 250,
            "like_count": 1200,
            "impression_count": 50000
        }
    },
    {
        "id": "1234567891",
        "text": "Fabric Protocol mainnet is officially live! Congratulations to the team 🚀",
        "author_id": "fabric_xyz",
        "created_at": datetime(2024, 1, 14, 12, 30, 0, tzinfo=timezone.utc),
        "public_metrics": {
            "retweet_count": 100,
            "like_count": 500,
            "impression_count": 20000
        }
    },
    {
        "id": "1234567892",
        "text": "GM! Another great day in crypto. Building continues.",
        "author_id": "crypto_enthusiast",
        "created_at": datetime(2024, 1, 13, 8, 0, 0, tzinfo=timezone.utc),
        "public_metrics": {
            "retweet_count": 5,
            "like_count": 20,
            "impression_count": 500
        }
    }
]

# Sample Article Content (Full Text)
SAMPLE_ARTICLES = {
    "high_confidence_tge": """
    Title: Caldera Announces Token Generation Event for January 22

    Caldera Labs, the team behind the popular Layer 2 rollup platform, has announced
    their highly anticipated Token Generation Event (TGE). The event is scheduled for
    January 22, 2024, at 12:00 PM UTC.

    Key Details:
    - Token Symbol: $CAL
    - Initial Distribution: 100 million tokens
    - Airdrop Allocation: 15% to early users
    - Trading: Live immediately on Uniswap and Camelot DEX

    Eligibility Criteria:
    Wallets that interacted with Caldera's testnet or deployed contracts before
    December 31, 2023, will be eligible for the airdrop. Users can check their
    eligibility at claim.caldera.xyz starting January 20.

    The team emphasized their commitment to fair distribution and preventing bot abuse.
    All claims will be verified through on-chain activity.
    """,

    "medium_confidence": """
    Title: Fabric Protocol Launches Mainnet with Advanced Features

    Fabric Protocol successfully launched its mainnet today, introducing several
    innovative features for decentralized application developers. The protocol focuses
    on privacy-preserving computations using advanced cryptography.

    While the mainnet is now live, the team has indicated that tokenomics details
    will be revealed in a future announcement. Community members are encouraged to
    participate in governance discussions on the Fabric Forum.

    The launch includes support for zero-knowledge proofs, homomorphic encryption,
    and secure multi-party computation.
    """,

    "low_confidence": """
    Title: Weekly Crypto Market Analysis

    This week saw continued momentum in the cryptocurrency markets. Bitcoin maintained
    its position above $42,000, while Ethereum showed strength at $2,200.

    DeFi protocols continue to attract investment, with total value locked increasing
    by 5% week-over-week. Layer 2 solutions are gaining traction as users seek lower
    transaction fees.

    Analysts remain cautiously optimistic about Q1 2024, citing improving macroeconomic
    conditions and increasing institutional adoption.
    """,

    "false_positive_game": """
    Title: New Blockchain Game Announces In-Game Token Drop

    CryptoQuest, a popular blockchain-based RPG, announced a special in-game token
    drop event for this weekend. Players can earn QUEST tokens by completing special
    missions and defeating rare monsters.

    The game token can be used to purchase cosmetic items, unlock new areas, and
    participate in special events. This is not a tradeable cryptocurrency but rather
    an in-game reward system.
    """
}

# Expected Relevance Scores
EXPECTED_RELEVANCE = {
    "high_confidence_tge": {
        "is_relevant": True,
        "min_confidence": 0.75,
        "matched_companies": ["Caldera"],
        "matched_keywords_count": 3,
        "has_token_symbol": True
    },
    "medium_confidence": {
        "is_relevant": False,  # No explicit TGE announcement
        "min_confidence": 0.3,
        "max_confidence": 0.6,
        "matched_companies": ["Fabric"],
        "matched_keywords_count": 0
    },
    "low_confidence": {
        "is_relevant": False,
        "max_confidence": 0.3,
        "matched_companies": [],
        "matched_keywords_count": 0
    },
    "false_positive_game": {
        "is_relevant": False,
        "max_confidence": 0.4,  # Should be reduced by exclusion patterns
        "has_exclusion": True
    }
}

# Mock RSS Feed Response
MOCK_RSS_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Crypto News Feed</title>
        <link>https://example.com</link>
        <description>Latest cryptocurrency news</description>
        <item>
            <title>Caldera Announces Token Generation Event</title>
            <link>https://example.com/caldera-tge</link>
            <description>Caldera Labs announces their TGE scheduled for next week</description>
            <pubDate>Mon, 15 Jan 2024 12:00:00 GMT</pubDate>
        </item>
    </channel>
</rss>
"""

# Cache Test Data
CACHE_TEST_DATA = {
    "articles": {
        "abc123": {
            "content": "Cached article content",
            "cached_at": "2024-01-15T12:00:00Z",
            "length": 100
        }
    },
    "summaries": {}
}

# State Test Data
STATE_TEST_DATA = {
    "seen_urls": {
        "https://example.com/article1": "2024-01-15T10:00:00Z",
        "https://example.com/article2": "2024-01-15T11:00:00Z"
    },
    "feed_stats": {
        "feed_hash_123": {
            "url": "https://example.com/feed.xml",
            "success_count": 10,
            "failure_count": 1,
            "tge_found": 3,
            "last_success": "2024-01-15T12:00:00Z"
        }
    },
    "last_full_scan": "2024-01-15T12:00:00Z"
}


def get_sample_company(name: str = "Caldera") -> Dict:
    """Get a sample company by name"""
    for company in SAMPLE_COMPANIES:
        if company["name"] == name:
            return company.copy()
    return SAMPLE_COMPANIES[0].copy()


def get_sample_feed_entry(index: int = 0) -> Dict:
    """Get a sample feed entry by index"""
    return SAMPLE_FEED_ENTRIES[index].copy()


def get_sample_tweet(index: int = 0) -> Dict:
    """Get a sample tweet by index"""
    return SAMPLE_TWEETS[index].copy()


def get_sample_article(article_type: str = "high_confidence_tge") -> str:
    """Get sample article content by type"""
    return SAMPLE_ARTICLES.get(article_type, SAMPLE_ARTICLES["high_confidence_tge"])
