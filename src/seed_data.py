"""
Seed database with initial data from config.py
"""
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.models import Company, Feed
from src.database import SessionLocal
from config import COMPANIES, NEWS_SOURCES, COMPANY_TWITTERS, CORE_NEWS_TWITTERS

logger = logging.getLogger(__name__)


def seed_companies(db: Session) -> dict:
    """Seed companies from config.py"""
    added = 0
    skipped = 0
    errors = []

    for company_data in COMPANIES:
        try:
            # Check if company already exists
            existing = db.query(Company).filter(Company.name == company_data["name"]).first()
            if existing:
                logger.info(f"Company {company_data['name']} already exists, skipping")
                skipped += 1
                continue

            # Get Twitter handle from COMPANY_TWITTERS mapping
            twitter_handle = COMPANY_TWITTERS.get(company_data["name"], "")

            # Create company
            company = Company(
                name=company_data["name"],
                aliases=company_data.get("aliases", []),
                tokens=company_data.get("tokens", []),
                exclusions=company_data.get("exclusions", []),
                priority=company_data.get("priority", "MEDIUM"),
                status=company_data.get("status", "active"),
                twitter_handle=twitter_handle,
                description=f"{company_data.get('status', 'Active')} project - Priority: {company_data.get('priority', 'MEDIUM')}"
            )

            db.add(company)
            db.commit()
            logger.info(f"Added company: {company_data['name']}")
            added += 1

        except IntegrityError as e:
            db.rollback()
            logger.warning(f"Company {company_data['name']} already exists (integrity error)")
            skipped += 1
        except Exception as e:
            db.rollback()
            error_msg = f"Error adding company {company_data['name']}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

    return {
        "added": added,
        "skipped": skipped,
        "errors": errors,
        "total": len(COMPANIES)
    }


def seed_feeds(db: Session) -> dict:
    """Seed feeds from config.py"""
    added = 0
    skipped = 0
    errors = []

    # Seed RSS news feeds
    for source_url in NEWS_SOURCES:
        try:
            # Extract name from URL (basic parsing)
            name = source_url.split("//")[-1].split("/")[0].replace("www.", "").replace(".com", "").replace(".co", "").title()

            # Check if feed already exists
            existing = db.query(Feed).filter(Feed.url == source_url).first()
            if existing:
                logger.info(f"Feed {name} already exists, skipping")
                skipped += 1
                continue

            feed = Feed(
                name=f"{name} RSS Feed",
                url=source_url,
                feed_type="rss",
                status="active",
                priority="MEDIUM"
            )

            db.add(feed)
            db.commit()
            logger.info(f"Added feed: {name}")
            added += 1

        except IntegrityError:
            db.rollback()
            logger.warning(f"Feed {source_url} already exists (integrity error)")
            skipped += 1
        except Exception as e:
            db.rollback()
            error_msg = f"Error adding feed {source_url}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

    # Seed Twitter feeds for news sources
    for twitter_handle in CORE_NEWS_TWITTERS:
        try:
            name = twitter_handle.replace("@", "")

            # Check if feed already exists
            existing = db.query(Feed).filter(Feed.url == twitter_handle).first()
            if existing:
                logger.info(f"Twitter feed {twitter_handle} already exists, skipping")
                skipped += 1
                continue

            feed = Feed(
                name=f"{name} Twitter",
                url=twitter_handle,
                feed_type="twitter",
                status="active",
                priority="HIGH"
            )

            db.add(feed)
            db.commit()
            logger.info(f"Added Twitter feed: {twitter_handle}")
            added += 1

        except IntegrityError:
            db.rollback()
            logger.warning(f"Twitter feed {twitter_handle} already exists (integrity error)")
            skipped += 1
        except Exception as e:
            db.rollback()
            error_msg = f"Error adding Twitter feed {twitter_handle}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

    return {
        "added": added,
        "skipped": skipped,
        "errors": errors,
        "total": len(NEWS_SOURCES) + len(CORE_NEWS_TWITTERS)
    }


def seed_all_data() -> dict:
    """Seed all data from config.py"""
    db = SessionLocal()
    try:
        logger.info("Starting data seeding...")

        companies_result = seed_companies(db)
        feeds_result = seed_feeds(db)

        result = {
            "success": True,
            "companies": companies_result,
            "feeds": feeds_result,
            "summary": {
                "total_added": companies_result["added"] + feeds_result["added"],
                "total_skipped": companies_result["skipped"] + feeds_result["skipped"],
                "total_errors": len(companies_result["errors"]) + len(feeds_result["errors"])
            }
        }

        logger.info(f"Seeding complete: {result['summary']}")
        return result

    except Exception as e:
        logger.error(f"Error during seeding: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()


if __name__ == "__main__":
    # Allow running as standalone script
    logging.basicConfig(level=logging.INFO)
    result = seed_all_data()
    print(f"Seeding result: {result}")
