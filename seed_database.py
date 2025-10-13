#!/usr/bin/env python3
"""
Standalone script to seed the database with companies and feeds from config.py
Run this script directly: python seed_database.py
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import Base, Company, Feed
from config import COMPANIES, NEWS_SOURCES, COMPANY_TWITTERS, CORE_NEWS_TWITTERS

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/tge_monitor")

print("🚀 Starting database seeding...")
print(f"📊 Database: {DATABASE_URL}")

# Create engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created/verified")

    # Seed Companies
    print(f"\n📦 Seeding {len(COMPANIES)} companies...")
    companies_added = 0
    companies_skipped = 0

    for company_data in COMPANIES:
        existing = db.query(Company).filter(Company.name == company_data["name"]).first()
        if existing:
            print(f"  ⏭️  {company_data['name']} - already exists")
            companies_skipped += 1
            continue

        twitter_handle = COMPANY_TWITTERS.get(company_data["name"], "")

        company = Company(
            name=company_data["name"],
            aliases=company_data.get("aliases", []),
            tokens=company_data.get("tokens", []),
            exclusions=company_data.get("exclusions", []),
            priority=company_data.get("priority", "MEDIUM"),
            status=company_data.get("status", "active"),
            twitter_handle=twitter_handle,
            description=f"{company_data.get('status', 'Active')} - {company_data.get('priority', 'MEDIUM')} priority"
        )

        db.add(company)
        print(f"  ✅ {company_data['name']} - added")
        companies_added += 1

    db.commit()
    print(f"\n✅ Companies: {companies_added} added, {companies_skipped} skipped")

    # Seed RSS Feeds
    print(f"\n📰 Seeding {len(NEWS_SOURCES)} RSS news feeds...")
    feeds_added = 0
    feeds_skipped = 0

    for source_url in NEWS_SOURCES:
        existing = db.query(Feed).filter(Feed.url == source_url).first()
        if existing:
            feeds_skipped += 1
            continue

        # Extract name from URL
        name = source_url.split("//")[-1].split("/")[0].replace("www.", "").replace(".com", "").replace(".co", "").title()

        feed = Feed(
            name=f"{name} RSS",
            url=source_url,
            feed_type="rss",
            status="active",
            priority="MEDIUM",
            is_active=True
        )

        db.add(feed)
        print(f"  ✅ {name} RSS")
        feeds_added += 1

    db.commit()

    # Seed Twitter Feeds
    print(f"\n🐦 Seeding {len(CORE_NEWS_TWITTERS)} Twitter news accounts...")

    for twitter_handle in CORE_NEWS_TWITTERS:
        existing = db.query(Feed).filter(Feed.url == twitter_handle).first()
        if existing:
            feeds_skipped += 1
            continue

        name = twitter_handle.replace("@", "")

        feed = Feed(
            name=f"{name} Twitter",
            url=twitter_handle,
            feed_type="twitter",
            status="active",
            priority="HIGH",
            is_active=True
        )

        db.add(feed)
        print(f"  ✅ {twitter_handle}")
        feeds_added += 1

    db.commit()
    print(f"\n✅ Feeds: {feeds_added} added, {feeds_skipped} skipped")

    print("\n" + "="*50)
    print("✅ DATABASE SEEDING COMPLETE!")
    print("="*50)
    print(f"📊 Summary:")
    print(f"   Companies: {companies_added} added, {companies_skipped} skipped")
    print(f"   Feeds: {feeds_added} added, {feeds_skipped} skipped")
    print(f"   Total: {companies_added + feeds_added} items added to database")
    print("="*50)

except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
