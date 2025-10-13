#!/usr/bin/env python3
"""
Check what's in the database
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import Company, Feed

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/tge_monitor")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

print("📊 DATABASE CONTENTS\n")
print("="*60)

# Check companies
companies = db.query(Company).all()
print(f"\n🏢 COMPANIES ({len(companies)} total):\n")
for company in companies:
    print(f"  • {company.name}")
    print(f"    Aliases: {', '.join(company.aliases) if company.aliases else 'None'}")
    print(f"    Tokens: {', '.join(company.tokens) if company.tokens else 'None'}")
    print(f"    Priority: {company.priority}, Status: {company.status}")
    print(f"    Twitter: {company.twitter_handle or 'None'}")
    print()

# Check feeds
feeds = db.query(Feed).all()
print(f"\n📰 FEEDS ({len(feeds)} total):\n")
rss_feeds = [f for f in feeds if f.feed_type == "rss"]
twitter_feeds = [f for f in feeds if f.feed_type == "twitter"]

print(f"RSS Feeds: {len(rss_feeds)}")
for feed in rss_feeds[:5]:  # Show first 5
    print(f"  • {feed.name}: {feed.url}")
print(f"  ... and {len(rss_feeds) - 5} more" if len(rss_feeds) > 5 else "")

print(f"\nTwitter Feeds: {len(twitter_feeds)}")
for feed in twitter_feeds[:5]:  # Show first 5
    print(f"  • {feed.name}: {feed.url}")
print(f"  ... and {len(twitter_feeds) - 5} more" if len(twitter_feeds) > 5 else "")

print("\n" + "="*60)

db.close()
