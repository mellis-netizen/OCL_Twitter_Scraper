#!/usr/bin/env python3
"""
Optimized Crypto TGE Monitor
Enhanced version with improved scraping, matching logic, and performance
"""

import os
import sys
import json
import logging
import schedule
import time
import signal
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple
import argparse
import hashlib
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import re

# Import configurations
from config import (
    EMAIL_CONFIG, TWITTER_CONFIG, LOG_CONFIG, SWARM_CONFIG,
    COMPANIES, TGE_KEYWORDS, NEWS_SOURCES,
    HIGH_CONFIDENCE_TGE_KEYWORDS, MEDIUM_CONFIDENCE_TGE_KEYWORDS,
    LOW_CONFIDENCE_TGE_KEYWORDS, EXCLUSION_PATTERNS
)

# Import optimized modules
from .twitter_monitor_optimized import OptimizedTwitterMonitor
from .news_scraper_optimized import OptimizedNewsScraper
from .email_notifier import EmailNotifier

# Import swarm coordination
from .swarm_integration import SwarmCoordinationHooks

# Import database models for saving alerts
from .database import DatabaseManager
from .models import Alert, Company

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


class OptimizedCryptoTGEMonitor:
    """Enhanced TGE monitoring system with optimized detection capabilities."""

    def __init__(self, swarm_enabled: bool = None):
        # Initialize swarm coordination
        self.swarm_hooks = SwarmCoordinationHooks(
            enabled=swarm_enabled if swarm_enabled is not None else SWARM_CONFIG['enabled'],
            session_id=SWARM_CONFIG.get('session_id')
        )

        # Restore swarm session if enabled
        if self.swarm_hooks.enabled:
            self.swarm_hooks.session_restore()
            logger.info("Swarm coordination enabled for TGE monitor")

        self.email_notifier = EmailNotifier(EMAIL_CONFIG)
        self.news_scraper = OptimizedNewsScraper(COMPANIES, TGE_KEYWORDS, NEWS_SOURCES)

        # Pass swarm hooks to scrapers
        if hasattr(self.news_scraper, 'set_swarm_hooks'):
            self.news_scraper.set_swarm_hooks(self.swarm_hooks)
        
        # Initialize Twitter monitor if configured
        self.twitter_monitor = None
        if TWITTER_CONFIG['bearer_token'] and not os.getenv('DISABLE_TWITTER'):
            try:
                self.twitter_monitor = OptimizedTwitterMonitor(
                    TWITTER_CONFIG['bearer_token'],
                    COMPANIES,
                    TGE_KEYWORDS
                )

                # Pass swarm hooks to Twitter monitor
                if hasattr(self.twitter_monitor, 'set_swarm_hooks'):
                    self.twitter_monitor.set_swarm_hooks(self.swarm_hooks)

                logger.info("Twitter monitoring enabled with optimizations")
            except Exception as e:
                logger.error(f"Failed to initialize Twitter monitor: {str(e)}")
        
        # State management
        self.state_file = 'state/monitor_state.json'
        self.state = self.load_state()
        self.running = False
        
        # Enhanced matching patterns
        self.compile_matching_patterns()
        
        # Performance tracking
        self.metrics = defaultdict(int)
        self.start_time = None
    
    def load_state(self) -> Dict:
        """Load monitor state."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading state: {str(e)}")
        
        return {
            'seen_hashes': {},
            'weekly_stats': {},
            'last_summary_date': None,
            'alert_history': []
        }
    
    def save_state(self):
        """Save monitor state."""
        try:
            os.makedirs('state', exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state: {str(e)}")
    
    def compile_matching_patterns(self):
        """Compile regex patterns for enhanced matching."""
        # Company patterns with word boundaries
        self.company_patterns = {}
        for company in COMPANIES:
            terms = [company['name']] + company.get('aliases', [])
            pattern = r'\b(' + '|'.join(re.escape(term) for term in terms) + r')\b'
            self.company_patterns[company['name']] = re.compile(pattern, re.IGNORECASE)
        
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
            for company in COMPANIES:
                for token in company.get('tokens', []):
                    if f"${token.upper()}" in token_matches:
                        info['matched_companies'].append(company['name'])
                        info['confidence'] += 25
                        info['strategy'].append('token_symbol_match')
        
        # Strategy 2: Company detection with context
        for company_name, pattern in self.company_patterns.items():
            if pattern.search(text):
                if company_name not in info['matched_companies']:
                    info['matched_companies'].append(company_name)
                info['confidence'] += 20
                
                # Get company priority
                company_data = next((c for c in COMPANIES if c['name'] == company_name), None)
                if company_data and company_data.get('priority') == 'HIGH':
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
            high_priority_companies = [c for c in info['matched_companies'] 
                                     if any(comp['name'] == c and comp.get('priority') == 'HIGH' 
                                           for comp in COMPANIES)]
            if high_priority_companies:
                threshold -= 10  # Lower threshold for high-priority companies
        
        is_relevant = info['confidence'] >= threshold
        
        return is_relevant, info['confidence'] / 100, info
    
    def deduplicate_content(self, content: str, url: str = "") -> bool:
        """
        Advanced deduplication to prevent duplicate alerts.
        Returns True if content is unique (should be processed).
        """
        # Create content hash
        content_hash = hashlib.sha256(content.lower().encode()).hexdigest()
        
        # Check exact match
        if content_hash in self.state['seen_hashes']:
            return False
        
        # Check URL if provided
        if url:
            url_hash = hashlib.sha256(url.encode()).hexdigest()
            if url_hash in self.state['seen_hashes']:
                return False
        
        # Fuzzy matching for similar content
        content_words = set(content.lower().split())
        if len(content_words) > 20:  # Only for substantial content
            for seen_hash, seen_data in list(self.state['seen_hashes'].items())[-100:]:
                if 'words' in seen_data:
                    seen_words = set(seen_data['words'])
                    similarity = len(content_words & seen_words) / len(content_words | seen_words)
                    
                    if similarity > 0.85:  # 85% similarity threshold
                        logger.debug(f"Similar content detected (similarity: {similarity:.2%})")
                        return False
        
        # Mark as seen
        self.state['seen_hashes'][content_hash] = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'words': list(content_words)[:100] if len(content_words) > 20 else []
        }
        
        if url:
            url_hash = hashlib.sha256(url.encode()).hexdigest()
            self.state['seen_hashes'][url_hash] = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'type': 'url'
            }
        
        # Clean old hashes (>30 days)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        self.state['seen_hashes'] = {
            k: v for k, v in self.state['seen_hashes'].items()
            if v.get('timestamp', '') > cutoff
        }
        
        return True
    
    def process_alerts(self, items: List[Dict], source: str) -> List[Dict]:
        """Process and filter alerts with enhanced analysis."""
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
                # Prepare alert
                alert = {
                    'source': source,
                    'content': content[:1000],  # Limit content length
                    'url': url,
                    'confidence': confidence,
                    'analysis': analysis_info,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'title': item.get('title', 'TGE Alert')
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
        
        # Sort by confidence
        alerts.sort(key=lambda x: x['confidence'], reverse=True)

        return alerts

    def save_alerts_to_database(self, alerts: List[Dict]) -> int:
        """Save alerts to the database."""
        saved_count = 0

        try:
            with DatabaseManager.get_session() as db:
                # Get company name to ID mapping
                companies = db.query(Company).all()
                company_map = {c.name: c.id for c in companies}

                for alert_data in alerts:
                    try:
                        # Determine urgency level based on confidence
                        confidence = alert_data['confidence']
                        if confidence >= 0.8:
                            urgency = 'critical'
                        elif confidence >= 0.7:
                            urgency = 'high'
                        elif confidence >= 0.5:
                            urgency = 'medium'
                        else:
                            urgency = 'low'

                        # Get first matched company ID
                        company_id = None
                        matched_companies = alert_data['analysis'].get('matched_companies', [])
                        if matched_companies:
                            for company_name in matched_companies:
                                if company_name in company_map:
                                    company_id = company_map[company_name]
                                    break

                        # Create alert object
                        db_alert = Alert(
                            title=alert_data.get('title', 'TGE Alert')[:500],
                            content=alert_data.get('content', '')[:10000],
                            source=alert_data['source'],
                            source_url=alert_data.get('url', ''),
                            confidence=confidence,
                            company_id=company_id,
                            keywords_matched=alert_data['analysis'].get('matched_keywords', []),
                            tokens_mentioned=alert_data['analysis'].get('token_symbols', []),
                            analysis_data=alert_data['analysis'],
                            urgency_level=urgency,
                            status='active'
                        )

                        db.add(db_alert)
                        saved_count += 1

                    except Exception as e:
                        logger.error(f"Error saving individual alert: {str(e)}")
                        continue

                db.commit()
                logger.info(f"Successfully saved {saved_count} alerts to database")

        except Exception as e:
            logger.error(f"Error saving alerts to database: {str(e)}")

        return saved_count

    def run_monitoring_cycle(self):
        """Execute one complete monitoring cycle."""
        cycle_start = time.time()
        logger.info("=" * 60)
        logger.info("Starting optimized monitoring cycle")

        # Pre-task hook
        task_id = self.swarm_hooks.pre_task("TGE monitoring cycle - news and Twitter scraping")

        try:
            all_alerts = []
            
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
                            news_alerts = self.process_alerts(articles, 'news')
                            all_alerts.extend(news_alerts)
                        else:  # Twitter
                            tweets = future.result()
                            logger.info(f"Fetched {len(tweets)} tweets")
                            twitter_alerts = self.process_alerts(tweets, 'twitter')
                            all_alerts.extend(twitter_alerts)
                    except Exception as e:
                        logger.error(f"Error in scraper {i}: {str(e)}")
            
            # Send alerts if any
            if all_alerts:
                logger.info(f"Sending {len(all_alerts)} TGE alerts")
                
                # Group by confidence tier
                high_confidence = [a for a in all_alerts if a['confidence'] >= 0.7]
                medium_confidence = [a for a in all_alerts if 0.4 <= a['confidence'] < 0.7]
                
                # Save alerts to database
                saved_count = self.save_alerts_to_database(all_alerts)
                logger.info(f"Saved {saved_count} alerts to database")

                # Send email
                success = self.email_notifier.send_tge_alerts(
                    all_alerts,
                    high_priority_count=len(high_confidence),
                    medium_priority_count=len(medium_confidence)
                )

                if success:
                    # Update state
                    self.state['alert_history'].extend([
                        {
                            'timestamp': a['timestamp'],
                            'companies': a['analysis']['matched_companies'],
                            'confidence': a['confidence']
                        } for a in all_alerts
                    ])

                    # Keep only recent history
                    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
                    self.state['alert_history'] = [
                        h for h in self.state['alert_history']
                        if h['timestamp'] > cutoff
                    ]
            else:
                logger.info("No TGE-related content found in this cycle")
            
            # Update metrics
            cycle_time = time.time() - cycle_start
            self.metrics['total_cycles'] += 1
            self.metrics['total_cycle_time'] += cycle_time
            self.metrics['last_cycle_time'] = cycle_time

            # Prepare metrics for swarm
            cycle_metrics = {
                'cycle_time': cycle_time,
                'alerts_found': len(all_alerts),
                'high_confidence_alerts': len([a for a in all_alerts if a['confidence'] >= 0.7]),
                'news_articles_processed': self.metrics.get('news_articles_processed', 0),
                'tweets_processed': self.metrics.get('tweets_processed', 0)
            }

            # Post-task hook (successful)
            self.swarm_hooks.post_task(task_id, status='completed', metrics=cycle_metrics)

            # Store cycle results in shared memory for other agents
            self.swarm_hooks.memory_store(
                'latest_cycle_results',
                {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'alerts': len(all_alerts),
                    'metrics': cycle_metrics
                },
                ttl=3600,
                shared=True
            )

            # Notify swarm of completion
            self.swarm_hooks.notify(
                f"Monitoring cycle completed: {len(all_alerts)} alerts in {cycle_time:.1f}s",
                level='success' if len(all_alerts) > 0 else 'info'
            )

            # Save state
            self.save_state()

            # Log performance
            logger.info(f"Monitoring cycle completed in {cycle_time:.1f}s")
            logger.info(f"Total alerts sent: {len(all_alerts)}")
            if all_alerts:
                confidence_dist = defaultdict(int)
                for alert in all_alerts:
                    tier = f"{int(alert['confidence']*100)//10*10}-{int(alert['confidence']*100)//10*10+9}%"
                    confidence_dist[tier] += 1
                logger.info(f"Confidence distribution: {dict(confidence_dist)}")

        except Exception as e:
            logger.error(f"Error in monitoring cycle: {str(e)}", exc_info=True)
            self.metrics['error_cycles'] += 1

            # Post-task hook (failed)
            self.swarm_hooks.post_task(
                task_id,
                status='failed',
                metrics={'error': str(e), 'cycle_time': time.time() - cycle_start}
            )

            # Notify swarm of error
            self.swarm_hooks.notify(f"Monitoring cycle failed: {str(e)}", level='error')
    
    def send_weekly_summary(self):
        """Send comprehensive weekly summary."""
        try:
            # Calculate statistics
            week_start = datetime.now(timezone.utc) - timedelta(days=7)
            week_alerts = [
                a for a in self.state.get('alert_history', [])
                if a['timestamp'] > week_start.isoformat()
            ]
            
            # Company statistics
            company_stats = defaultdict(int)
            confidence_stats = defaultdict(int)
            
            for alert in week_alerts:
                for company in alert.get('companies', []):
                    company_stats[company] += 1
                confidence_tier = f"{int(alert['confidence']*100)//10*10}%+"
                confidence_stats[confidence_tier] += 1
            
            # Health report
            health_report = self.news_scraper.get_feed_health_report()
            
            # Send summary
            self.email_notifier.send_weekly_summary(
                total_alerts=len(week_alerts),
                company_breakdown=dict(company_stats),
                confidence_breakdown=dict(confidence_stats),
                health_report=health_report,
                performance_metrics={
                    'avg_cycle_time': self.metrics['total_cycle_time'] / max(self.metrics['total_cycles'], 1),
                    'error_rate': self.metrics['error_cycles'] / max(self.metrics['total_cycles'], 1),
                    'uptime': (time.time() - self.start_time) / 3600 if self.start_time else 0
                }
            )
            
            # Update state
            self.state['last_summary_date'] = datetime.now(timezone.utc).isoformat()
            self.save_state()
            
        except Exception as e:
            logger.error(f"Error sending weekly summary: {str(e)}")
    
    def run_continuous(self):
        """Run continuous monitoring with weekly schedule."""
        self.running = True
        self.start_time = time.time()
        
        logger.info("Starting optimized TGE monitor in continuous mode")
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
        """Graceful shutdown."""
        logger.info("Shutting down TGE monitor")
        self.running = False
        self.save_state()

        # End swarm session
        if self.swarm_hooks.enabled:
            self.swarm_hooks.session_end(export_metrics=True)
            logger.info("Swarm session ended")


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(description="Optimized Crypto TGE Monitor")
    parser.add_argument('--mode', choices=['once', 'continuous', 'test', 'status'],
                       default='once', help='Monitoring mode')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()
    
    # Adjust logging if verbose
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize monitor
    monitor = OptimizedCryptoTGEMonitor()
    
    # Signal handling
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        monitor.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Execute based on mode
    if args.mode == 'once':
        logger.info("Running single monitoring cycle")
        monitor.run_monitoring_cycle()
    elif args.mode == 'continuous':
        monitor.run_continuous()
    elif args.mode == 'test':
        logger.info("Running in test mode")
        # Test with sample content
        test_content = "Exciting news! Caldera is launching their TGE next week. The $CAL token will be available for trading on major exchanges."
        is_relevant, confidence, info = monitor.enhanced_content_analysis(test_content, "test")
        logger.info(f"Test analysis: relevant={is_relevant}, confidence={confidence:.0%}")
        logger.info(f"Analysis details: {json.dumps(info, indent=2)}")
    elif args.mode == 'status':
        # Show system status
        logger.info("System Status Report")
        logger.info("=" * 50)
        
        # Check feed health
        health = monitor.news_scraper.get_feed_health_report()
        logger.info(f"Total feeds: {health['total_feeds']}")
        logger.info(f"Healthy feeds: {health['healthy_feeds']}")
        logger.info(f"Failing feeds: {health['failing_feeds']}")
        
        if health['top_performers']:
            logger.info("\nTop performing feeds:")
            for feed in health['top_performers'][:5]:
                logger.info(f"  - {feed['url']}: {feed['tge_found']} TGEs found")
        
        # Check recent alerts
        recent_alerts = monitor.state.get('alert_history', [])[-10:]
        if recent_alerts:
            logger.info(f"\nRecent alerts: {len(recent_alerts)}")
            for alert in recent_alerts[-5:]:
                logger.info(f"  - {alert['timestamp']}: {alert['companies']} ({alert['confidence']:.0%})")


if __name__ == "__main__":
    main()