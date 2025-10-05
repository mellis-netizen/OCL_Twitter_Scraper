"""
Enhanced Optimized Crypto TGE Monitor with Database Integration
Replaces file-based storage with PostgreSQL database
"""

import os
import sys
import json
import logging
import schedule
import time
import signal
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

# Import configurations
from config import (
    EMAIL_CONFIG, TWITTER_CONFIG, LOG_CONFIG,
    COMPANIES, TGE_KEYWORDS, NEWS_SOURCES,
    HIGH_CONFIDENCE_TGE_KEYWORDS, MEDIUM_CONFIDENCE_TGE_KEYWORDS,
    LOW_CONFIDENCE_TGE_KEYWORDS, EXCLUSION_PATTERNS
)

# Import enhanced modules
from twitter_monitor_optimized import OptimizedTwitterMonitor
from news_scraper_optimized import OptimizedNewsScraper
from email_notifier import EmailNotifier

# Import database components
from database import init_db, DatabaseManager
from database_service import db_service
from models import Company, Alert, Feed, MonitoringSession

# Configure logging
def setup_logging():
    """Set up comprehensive logging configuration."""
    log_level = getattr(logging, LOG_CONFIG['level'].upper(), logging.INFO)
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_CONFIG['file']),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

logger = setup_logging()


class EnhancedCryptoTGEMonitor:
    """Enhanced TGE monitoring system with database integration and improved performance."""
    
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.db_service = db_service
        
        # Initialize database
        self._init_database()
        
        # Initialize components
        self.email_notifier = EmailNotifier(EMAIL_CONFIG)
        self.news_scraper = OptimizedNewsScraper(COMPANIES, TGE_KEYWORDS, NEWS_SOURCES)
        
        # Initialize Twitter monitor if configured
        self.twitter_monitor = None
        if TWITTER_CONFIG['bearer_token'] and not os.getenv('DISABLE_TWITTER'):
            try:
                self.twitter_monitor = OptimizedTwitterMonitor(
                    TWITTER_CONFIG['bearer_token'],
                    COMPANIES,
                    TGE_KEYWORDS
                )
                logger.info("Twitter monitoring enabled with database integration")
            except Exception as e:
                logger.error(f"Failed to initialize Twitter monitor: {str(e)}")
        
        # Enhanced matching patterns
        self.compile_matching_patterns()
        
        # Performance tracking with database
        self.metrics = defaultdict(int)
        self.start_time = None
        self.monitoring_session = None
        
        # Initialize monitoring session
        self._create_monitoring_session()
    
    def _init_database(self):
        """Initialize database and migrate legacy data if needed"""
        try:
            # Initialize database tables
            init_db()
            logger.info("Database initialized successfully")
            
            # Check if we need to migrate legacy data
            with DatabaseManager.get_session() as db:
                company_count = db.query(Company).count()
                
                if company_count == 0:
                    logger.info("No companies found in database, migrating from config...")
                    self._migrate_companies_from_config()
                    self._migrate_feeds_from_config()
                    
                    # Try to migrate legacy state files
                    try:
                        from database_service import migrate_from_file_storage
                        migration_results = migrate_from_file_storage()
                        logger.info(f"Legacy data migration results: {migration_results}")
                    except Exception as e:
                        logger.warning(f"Legacy data migration failed: {e}")
        
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def _migrate_companies_from_config(self):
        """Migrate companies from config to database"""
        for company_config in COMPANIES:
            try:
                self.db_service.create_or_update_company(company_config)
                logger.debug(f"Migrated company: {company_config['name']}")
            except Exception as e:
                logger.error(f"Failed to migrate company {company_config.get('name', 'unknown')}: {e}")
    
    def _migrate_feeds_from_config(self):
        """Migrate feeds from config to database"""
        for feed_url in NEWS_SOURCES:
            try:
                with DatabaseManager.get_session() as db:
                    existing = db.query(Feed).filter(Feed.url == feed_url).first()
                    if not existing:
                        # Determine feed priority based on URL
                        priority = self._get_feed_priority_from_url(feed_url)
                        
                        feed = Feed(
                            name=self._extract_feed_name(feed_url),
                            url=feed_url,
                            priority=priority,
                            is_active=True
                        )
                        db.add(feed)
                        db.commit()
                        logger.debug(f"Migrated feed: {feed_url}")
            except Exception as e:
                logger.error(f"Failed to migrate feed {feed_url}: {e}")
    
    def _extract_feed_name(self, url: str) -> str:
        """Extract feed name from URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            return domain.split('.')[0].title()
        except:
            return url[:50]
    
    def _get_feed_priority_from_url(self, url: str) -> int:
        """Determine feed priority based on URL"""
        tier_1_domains = ['theblock.co', 'decrypt.co', 'coindesk.com', 'thedefiant.io', 'bankless.com']
        tier_2_domains = ['cointelegraph.com', 'cryptobriefing.com', 'blockonomi.com']
        
        for domain in tier_1_domains:
            if domain in url:
                return 1
        
        for domain in tier_2_domains:
            if domain in url:
                return 2
        
        return 3  # Default priority
    
    def _create_monitoring_session(self):
        """Create new monitoring session in database"""
        try:
            self.monitoring_session = self.db_service.create_monitoring_session(self.session_id)
            logger.info(f"Created monitoring session: {self.session_id}")
        except Exception as e:
            logger.error(f"Failed to create monitoring session: {e}")
    
    def compile_matching_patterns(self):
        """Compile regex patterns for enhanced matching."""
        import re
        
        # Get companies from database
        companies = self.db_service.get_companies()
        
        # Company patterns with word boundaries
        self.company_patterns = {}
        for company in companies:
            terms = [company.name] + (company.aliases or [])
            pattern = r'\b(' + '|'.join(re.escape(term) for term in terms) + r')\b'
            self.company_patterns[company.name] = re.compile(pattern, re.IGNORECASE)
        
        # Token symbol pattern
        self.token_pattern = re.compile(r'\$[A-Z]{2,10}\b')
        
        # Date patterns for urgency detection
        self.date_patterns = [
            re.compile(r'\b(today|tomorrow|tonight)\b', re.IGNORECASE),
            re.compile(r'\b(this|next)\s+(week|monday|tuesday|wednesday|thursday|friday)\b', re.IGNORECASE),
            re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'),
            re.compile(r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}\b', re.IGNORECASE)
        ]
        
        # Exclusion patterns
        self.exclusion_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in EXCLUSION_PATTERNS]
    
    def enhanced_content_analysis(self, text: str, source_type: str = "unknown") -> Tuple[bool, float, Dict]:
        """
        Enhanced content analysis with multi-strategy matching and confidence scoring.
        Returns (is_relevant, confidence_score, detailed_info)
        """
        text_lower = text.lower()
        info = {
            'matched_companies': [],
            'matched_keywords': [],
            'confidence': 0,
            'strategy': [],
            'token_symbols': [],
            'urgency_indicators': [],
            'exclusions': []
        }
        
        # Strategy 1: Token symbol detection ($CAL, $FHE, etc.)
        token_matches = self.token_pattern.findall(text)
        if token_matches:
            info['token_symbols'] = token_matches
            info['confidence'] += 15
            
            # Check if symbols match company tokens
            companies = self.db_service.get_companies()
            for company in companies:
                for token in (company.tokens or []):
                    if f"${token.upper()}" in token_matches:
                        if company.name not in info['matched_companies']:
                            info['matched_companies'].append(company.name)
                        info['confidence'] += 25
                        info['strategy'].append('token_symbol_match')
        
        # Strategy 2: Company detection with context
        for company_name, pattern in self.company_patterns.items():
            if pattern.search(text):
                if company_name not in info['matched_companies']:
                    info['matched_companies'].append(company_name)
                info['confidence'] += 20
                
                # Get company from database for priority boost
                company = self.db_service.get_company_by_name(company_name)
                if company and company.priority == 'HIGH':
                    info['confidence'] += 10
                    info['strategy'].append('high_priority_company')
        
        # Strategy 3: Keyword matching with confidence tiers
        for keyword in HIGH_CONFIDENCE_TGE_KEYWORDS:
            if keyword.lower() in text_lower:
                info['matched_keywords'].append(keyword)
                info['confidence'] += 30
                info['strategy'].append('high_confidence_keyword')
        
        for keyword in MEDIUM_CONFIDENCE_TGE_KEYWORDS:
            if keyword.lower() in text_lower:
                info['matched_keywords'].append(keyword)
                info['confidence'] += 20
                info['strategy'].append('medium_confidence_keyword')
        
        for keyword in LOW_CONFIDENCE_TGE_KEYWORDS:
            if keyword.lower() in text_lower:
                info['matched_keywords'].append(keyword)
                info['confidence'] += 10
                info['strategy'].append('low_confidence_keyword')
        
        # Strategy 4: Urgency detection
        for pattern in self.date_patterns:
            if pattern.search(text):
                info['urgency_indicators'].append('date_mentioned')
                info['confidence'] += 15
                break
        
        # Strategy 5: Combined signals boost
        if info['matched_companies'] and info['matched_keywords']:
            info['confidence'] += 25
            info['strategy'].append('company_keyword_combo')
            
            # Proximity check
            for company in info['matched_companies']:
                if company in self.company_patterns:
                    company_pattern = self.company_patterns[company]
                    for keyword in info['matched_keywords']:
                        # Simple proximity check
                        company_match = company_pattern.search(text_lower)
                        keyword_pos = text_lower.find(keyword.lower())
                        
                        if company_match and keyword_pos >= 0:
                            distance = abs(company_match.start() - keyword_pos)
                            if distance < 200:  # Within ~200 characters
                                info['confidence'] += 20
                                info['strategy'].append('proximity_boost')
                                break
        
        # Apply exclusions
        for pattern in self.exclusion_patterns:
            if pattern.search(text):
                info['exclusions'].append('exclusion_found')
                info['confidence'] -= 30
        
        # Source type adjustments
        if source_type == "twitter" and "@" in text:
            # Tweets with mentions might be replies/discussions
            info['confidence'] -= 10
        elif source_type == "news" and len(text) > 1000:
            # Longer news articles are more likely to be comprehensive
            info['confidence'] += 10
        
        # Normalize confidence (0-100)
        info['confidence'] = max(0, min(100, info['confidence']))
        
        # Determine relevance with dynamic threshold
        threshold = 40  # Base threshold
        
        # Adjust threshold based on company priority
        if info['matched_companies']:
            companies = self.db_service.get_companies()
            high_priority_companies = [
                c for c in info['matched_companies'] 
                if any(comp.name == c and comp.priority == 'HIGH' for comp in companies)
            ]
            if high_priority_companies:
                threshold -= 10  # Lower threshold for high-priority companies
        
        is_relevant = info['confidence'] >= threshold
        
        return is_relevant, info['confidence'] / 100, info
    
    def deduplicate_content(self, content: str, url: str = "") -> bool:
        """
        Check for duplicate content using database and cache.
        Returns True if content is unique (should be processed).
        """
        # Create content hash
        content_hash = hashlib.sha256(content.lower().encode()).hexdigest()
        
        # Check using database service
        is_duplicate = self.db_service.check_duplicate_alert(content_hash, url)
        
        return not is_duplicate
    
    def process_alerts(self, items: List[Dict], source: str) -> List[Dict]:
        """Process and filter alerts with enhanced analysis and database storage."""
        alerts = []
        
        for item in items:
            # Determine content to analyze
            if source == "twitter":
                content = item.get('text', '')
                url = item.get('url', '')
            else:  # news
                # Prefer full content, fall back to summary + title
                content = item.get('content', '')
                if not content:
                    content = f"{item.get('title', '')} {item.get('summary', '')}"
                url = item.get('url', '')
            
            # Skip if no content
            if not content:
                continue
            
            # Check deduplication
            if not self.deduplicate_content(content, url):
                continue
            
            # Perform enhanced analysis
            is_relevant, confidence, analysis_info = self.enhanced_content_analysis(content, source)
            
            if is_relevant:
                # Prepare alert data for database
                alert_data = {
                    'title': item.get('title', content[:100] + '...' if len(content) > 100 else content),
                    'content': content[:2000],  # Limit content length for database
                    'source': source,
                    'source_url': url,
                    'confidence': confidence,
                    'keywords_matched': analysis_info['matched_keywords'],
                    'tokens_mentioned': analysis_info['token_symbols'],
                    'analysis_data': analysis_info,
                    'urgency_level': self._determine_urgency_level(confidence, analysis_info),
                    'company_name': analysis_info['matched_companies'][0] if analysis_info['matched_companies'] else None
                }
                
                # Add source-specific info
                if source == "twitter":
                    alert_data['metrics'] = item.get('metrics', {})
                else:
                    alert_data['feed_source'] = item.get('feed_title', 'Unknown')
                
                try:
                    # Store alert in database
                    db_alert = self.db_service.create_alert(alert_data)
                    
                    # Convert to response format
                    alert = {
                        'id': db_alert.id,
                        'source': source,
                        'content': content[:1000],  # Limit for email
                        'url': url,
                        'confidence': confidence,
                        'analysis': analysis_info,
                        'timestamp': db_alert.created_at.isoformat(),
                        'title': alert_data['title']
                    }
                    
                    # Add source-specific info
                    if source == "twitter":
                        alert['metrics'] = item.get('metrics', {})
                    else:
                        alert['feed_source'] = item.get('feed_title', 'Unknown')
                    
                    alerts.append(alert)
                    
                    # Update metrics
                    self.metrics[f'{source}_alerts'] += 1
                    self.metrics[f'confidence_{int(confidence*100)//10*10}'] += 1
                    
                    # Log high-confidence alerts
                    if confidence >= 0.7:
                        logger.info(f"High-confidence TGE alert ({confidence:.0%}): {analysis_info['matched_companies']}")
                
                except Exception as e:
                    logger.error(f"Failed to store alert in database: {e}")
        
        # Sort by confidence
        alerts.sort(key=lambda x: x['confidence'], reverse=True)
        
        return alerts
    
    def _determine_urgency_level(self, confidence: float, analysis_info: Dict) -> str:
        """Determine urgency level based on confidence and analysis"""
        if confidence >= 0.9:
            return 'critical'
        elif confidence >= 0.7:
            return 'high'
        elif confidence >= 0.5:
            return 'medium'
        else:
            return 'low'
    
    def run_monitoring_cycle(self):
        """Execute one complete monitoring cycle with database integration."""
        cycle_start = time.time()
        logger.info("=" * 60)
        logger.info("Starting enhanced monitoring cycle with database integration")
        
        try:
            all_alerts = []
            
            # Update monitoring session
            self.db_service.update_monitoring_session(
                self.session_id,
                status='running'
            )
            
            # Run scrapers in parallel
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = []
                
                # News scraping
                futures.append(executor.submit(self.news_scraper.fetch_all_articles, timeout=120))
                
                # Twitter monitoring
                if self.twitter_monitor:
                    futures.append(executor.submit(self.twitter_monitor.fetch_all_tweets, timeout=60))
                
                # Process results
                for i, future in enumerate(futures):
                    try:
                        if i == 0:  # News
                            articles = future.result()
                            logger.info(f"Fetched {len(articles)} news articles")
                            
                            # Update feed statistics
                            for article in articles:
                                feed_url = article.get('feed_url', 'unknown')
                                if feed_url != 'unknown':
                                    self.db_service.update_feed_stats(
                                        feed_url, 
                                        success=True, 
                                        article_count=1
                                    )
                            
                            news_alerts = self.process_alerts(articles, 'news')
                            all_alerts.extend(news_alerts)
                            
                            # Update session metrics
                            self.db_service.update_monitoring_session(
                                self.session_id,
                                articles_processed=len(articles)
                            )
                            
                        else:  # Twitter
                            tweets = future.result()
                            logger.info(f"Fetched {len(tweets)} tweets")
                            twitter_alerts = self.process_alerts(tweets, 'twitter')
                            all_alerts.extend(twitter_alerts)
                            
                            # Update session metrics
                            self.db_service.update_monitoring_session(
                                self.session_id,
                                tweets_processed=len(tweets)
                            )
                            
                    except Exception as e:
                        logger.error(f"Error in scraper {i}: {str(e)}")
                        self.db_service.update_monitoring_session(
                            self.session_id,
                            errors_encountered=self.metrics.get('error_cycles', 0) + 1
                        )
            
            # Send alerts if any
            if all_alerts:
                logger.info(f"Sending {len(all_alerts)} TGE alerts")
                
                # Group by confidence tier
                high_confidence = [a for a in all_alerts if a['confidence'] >= 0.7]
                medium_confidence = [a for a in all_alerts if 0.4 <= a['confidence'] < 0.7]
                
                # Send email
                success = self.email_notifier.send_tge_alerts(
                    all_alerts,
                    high_priority_count=len(high_confidence),
                    medium_priority_count=len(medium_confidence)
                )
                
                if success:
                    logger.info(f"Successfully sent {len(all_alerts)} alerts")
                
                # Update session metrics
                self.db_service.update_monitoring_session(
                    self.session_id,
                    alerts_generated=len(all_alerts)
                )
                
            else:
                logger.info("No TGE-related content found in this cycle")
            
            # Update performance metrics
            cycle_time = time.time() - cycle_start
            self.metrics['total_cycles'] += 1
            self.metrics['total_cycle_time'] += cycle_time
            self.metrics['last_cycle_time'] = cycle_time
            
            # Record system metrics in database
            self.db_service.record_metric(
                'monitoring', 'cycle_time', cycle_time, 'seconds'
            )
            self.db_service.record_metric(
                'monitoring', 'alerts_generated', len(all_alerts), 'count'
            )
            
            # Update monitoring session
            self.db_service.update_monitoring_session(
                self.session_id,
                status='completed'
            )
            
            # Log performance
            logger.info(f"Enhanced monitoring cycle completed in {cycle_time:.1f}s")
            logger.info(f"Total alerts sent: {len(all_alerts)}")
            if all_alerts:
                confidence_dist = defaultdict(int)
                for alert in all_alerts:
                    tier = f"{int(alert['confidence']*100)//10*10}-{int(alert['confidence']*100)//10*10+9}%"
                    confidence_dist[tier] += 1
                logger.info(f"Confidence distribution: {dict(confidence_dist)}")
            
        except Exception as e:
            logger.error(f"Error in enhanced monitoring cycle: {str(e)}", exc_info=True)
            self.metrics['error_cycles'] += 1
            
            # Update monitoring session with error
            self.db_service.update_monitoring_session(
                self.session_id,
                status='failed',
                errors_encountered=self.metrics.get('error_cycles', 0)
            )
    
    def send_weekly_summary(self):
        """Send comprehensive weekly summary with database statistics."""
        try:
            # Get statistics from database
            stats = self.db_service.get_statistics()
            
            # Get feed health report
            health_report = self.db_service.get_feed_health_report()
            
            # Get recent alerts for analysis
            recent_alerts = self.db_service.get_recent_alerts(hours=24*7)  # Last week
            
            # Calculate additional statistics
            if recent_alerts:
                company_stats = defaultdict(int)
                confidence_stats = defaultdict(int)
                
                for alert in recent_alerts:
                    if alert.company:
                        company_stats[alert.company.name] += 1
                    confidence_tier = f"{int(alert.confidence*100)//10*10}%+"
                    confidence_stats[confidence_tier] += 1
            else:
                company_stats = {}
                confidence_stats = {}
            
            # Send enhanced summary
            self.email_notifier.send_weekly_summary(
                total_alerts=stats.get('alerts_last_7d', 0),
                company_breakdown=dict(company_stats),
                confidence_breakdown=dict(confidence_stats),
                health_report=health_report,
                performance_metrics={
                    'avg_cycle_time': self.metrics['total_cycle_time'] / max(self.metrics['total_cycles'], 1),
                    'error_rate': self.metrics['error_cycles'] / max(self.metrics['total_cycles'], 1),
                    'uptime': (time.time() - self.start_time) / 3600 if self.start_time else 0,
                    'database_stats': stats
                }
            )
            
            logger.info("Weekly summary sent successfully")
            
        except Exception as e:
            logger.error(f"Error sending weekly summary: {str(e)}")
    
    def run_continuous(self):
        """Run continuous monitoring with database integration."""
        self.running = True
        self.start_time = time.time()
        
        logger.info("Starting enhanced TGE monitor with database integration")
        logger.info("Schedule: Weekly on Mondays at 8:00 AM PST")
        
        # Schedule monitoring
        schedule.every().monday.at("08:00").do(self.run_monitoring_cycle)
        
        # Schedule weekly summary (30 minutes after monitoring)
        schedule.every().monday.at("08:30").do(self.send_weekly_summary)
        
        # Run initial cycle
        logger.info("Running initial monitoring cycle")
        self.run_monitoring_cycle()
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def shutdown(self):
        """Graceful shutdown with database cleanup."""
        logger.info("Shutting down enhanced TGE monitor")
        self.running = False
        
        # Update final monitoring session status
        if self.monitoring_session:
            self.db_service.update_monitoring_session(
                self.session_id,
                status='shutdown'
            )


def main():
    """Main entry point with enhanced argument parsing."""
    parser = argparse.ArgumentParser(description="Enhanced Crypto TGE Monitor with Database")
    parser.add_argument('--mode', choices=['once', 'continuous', 'test', 'status', 'migrate'],
                       default='once', help='Monitoring mode')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--init-db', action='store_true', help='Initialize database tables')
    parser.add_argument('--migrate', action='store_true', help='Migrate legacy data to database')
    args = parser.parse_args()
    
    # Adjust logging if verbose
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Handle database initialization
    if args.init_db:
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialization complete")
        return
    
    # Handle migration
    if args.migrate or args.mode == 'migrate':
        logger.info("Migrating legacy data to database...")
        from database_service import migrate_from_file_storage
        results = migrate_from_file_storage()
        logger.info(f"Migration results: {results}")
        return
    
    # Initialize monitor
    monitor = EnhancedCryptoTGEMonitor()
    
    # Signal handling
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        monitor.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Execute based on mode
    if args.mode == 'once':
        logger.info("Running single enhanced monitoring cycle")
        monitor.run_monitoring_cycle()
    elif args.mode == 'continuous':
        monitor.run_continuous()
    elif args.mode == 'test':
        logger.info("Running in test mode with database integration")
        # Test with sample content
        test_content = "Caldera is excited to announce their TGE launching next week! The $CAL token will be distributed to community members."
        is_relevant, confidence, info = monitor.enhanced_content_analysis(test_content, "test")
        logger.info(f"Test analysis: relevant={is_relevant}, confidence={confidence:.0%}")
        logger.info(f"Analysis details: {json.dumps(info, indent=2)}")
        
        # Test database operations
        logger.info("Testing database operations...")
        stats = monitor.db_service.get_statistics()
        logger.info(f"Database statistics: {stats}")
        
    elif args.mode == 'status':
        # Enhanced system status with database information
        logger.info("Enhanced System Status Report")
        logger.info("=" * 50)
        
        # Database statistics
        stats = monitor.db_service.get_statistics()
        logger.info(f"Database Statistics:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
        
        # Feed health
        health = monitor.db_service.get_feed_health_report()
        logger.info(f"\nFeed Health:")
        logger.info(f"  Total feeds: {health['total_feeds']}")
        logger.info(f"  Active feeds: {health['active_feeds']}")
        logger.info(f"  Healthy feeds: {health['healthy_feeds']}")
        logger.info(f"  Failing feeds: {health['failing_feeds']}")
        
        if health['top_performers']:
            logger.info("\nTop performing feeds:")
            for feed in health['top_performers'][:5]:
                logger.info(f"  - {feed['name']}: {feed['tge_found']} TGEs found (Success rate: {feed['success_rate']:.1%})")
        
        # Recent alerts from database
        recent_alerts = monitor.db_service.get_recent_alerts(24)
        logger.info(f"\nRecent alerts (last 24h): {len(recent_alerts)}")
        for alert in recent_alerts[-5:]:
            logger.info(f"  - {alert.created_at}: {alert.title} ({alert.confidence:.0%})")


if __name__ == "__main__":
    main()