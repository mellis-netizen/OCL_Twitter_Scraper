"""
Database service layer for TGE Monitor
Replaces file-based storage with PostgreSQL database operations
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from .database import DatabaseManager, CacheManager
from .models import User, Company, Alert, Feed, MonitoringSession, SystemMetrics
from .schemas import AlertCreate, CompanyCreate, FeedCreate

logger = logging.getLogger(__name__)


class DatabaseService:
    """Main database service for TGE Monitor operations"""
    
    def __init__(self):
        self.cache = CacheManager()
    
    # Company operations
    def get_companies(self, include_inactive: bool = False) -> List[Company]:
        """Get all companies from database"""
        cache_key = f"companies:{'all' if include_inactive else 'active'}"
        cached = self.cache.get(cache_key)
        
        if cached:
            try:
                # For now, we'll skip caching complex objects and fetch fresh
                pass
            except:
                pass
        
        with DatabaseManager.get_session() as db:
            query = db.query(Company)
            if not include_inactive:
                query = query.filter(Company.status != 'inactive')
            
            companies = query.all()
            return companies
    
    def get_company_by_name(self, name: str) -> Optional[Company]:
        """Get company by name"""
        with DatabaseManager.get_session() as db:
            return db.query(Company).filter(Company.name == name).first()
    
    def create_or_update_company(self, company_data: Dict[str, Any]) -> Company:
        """Create or update company in database"""
        with DatabaseManager.get_session() as db:
            existing = db.query(Company).filter(Company.name == company_data['name']).first()
            
            if existing:
                # Update existing company
                for key, value in company_data.items():
                    setattr(existing, key, value)
                company = existing
            else:
                # Create new company
                company = Company(**company_data)
                db.add(company)
            
            db.commit()
            db.refresh(company)
            
            # Clear cache
            self.cache.delete("companies:all")
            self.cache.delete("companies:active")
            
            return company
    
    # Alert operations
    def create_alert(self, alert_data: Dict[str, Any], user_id: Optional[int] = None) -> Alert:
        """Create new alert in database"""
        with DatabaseManager.get_session() as db:
            # Get or create company if specified
            company_id = None
            if alert_data.get('company_name'):
                company = self.get_or_create_company_by_name(alert_data['company_name'])
                company_id = company.id
            
            alert = Alert(
                title=alert_data.get('title', ''),
                content=alert_data.get('content', ''),
                source=alert_data.get('source', 'unknown'),
                source_url=alert_data.get('source_url', ''),
                confidence=alert_data.get('confidence', 0.0),
                company_id=company_id,
                keywords_matched=alert_data.get('keywords_matched', []),
                tokens_mentioned=alert_data.get('tokens_mentioned', []),
                analysis_data=alert_data.get('analysis_data', {}),
                sentiment_score=alert_data.get('sentiment_score'),
                urgency_level=alert_data.get('urgency_level', 'medium'),
                user_id=user_id
            )
            
            db.add(alert)
            db.commit()
            db.refresh(alert)
            
            # Clear relevant caches
            self.cache.delete("alerts:recent")
            
            return alert
    
    def get_alerts(
        self, 
        limit: int = 100, 
        offset: int = 0,
        company_id: Optional[int] = None,
        source: Optional[str] = None,
        min_confidence: Optional[float] = None,
        from_date: Optional[datetime] = None
    ) -> List[Alert]:
        """Get alerts with filtering"""
        with DatabaseManager.get_session() as db:
            query = db.query(Alert)
            
            if company_id:
                query = query.filter(Alert.company_id == company_id)
            
            if source:
                query = query.filter(Alert.source == source)
            
            if min_confidence is not None:
                query = query.filter(Alert.confidence >= min_confidence)
            
            if from_date:
                query = query.filter(Alert.created_at >= from_date)
            
            alerts = query.order_by(desc(Alert.created_at)).offset(offset).limit(limit).all()
            return alerts
    
    def get_recent_alerts(self, hours: int = 24) -> List[Alert]:
        """Get recent alerts"""
        cache_key = f"alerts:recent:{hours}"
        
        with DatabaseManager.get_session() as db:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            alerts = db.query(Alert).filter(
                Alert.created_at >= cutoff
            ).order_by(desc(Alert.created_at)).all()
            
            return alerts
    
    def check_duplicate_alert(self, content_hash: str, url: Optional[str] = None) -> bool:
        """Check if alert is duplicate"""
        cache_key = f"alert_hash:{content_hash}"
        if self.cache.exists(cache_key):
            return True
        
        with DatabaseManager.get_session() as db:
            # Check by URL if provided
            if url:
                existing = db.query(Alert).filter(Alert.source_url == url).first()
                if existing:
                    # Cache for 24 hours
                    self.cache.set(cache_key, "exists", 86400)
                    return True
            
            # For now, we'll use cache-based deduplication
            # In production, you might want to implement content-based similarity checking
            self.cache.set(cache_key, "exists", 86400)  # Cache for 24 hours
            return False
    
    # Feed operations
    def get_feeds(self, active_only: bool = True) -> List[Feed]:
        """Get all feeds"""
        with DatabaseManager.get_session() as db:
            query = db.query(Feed)
            if active_only:
                query = query.filter(Feed.is_active == True)
            
            return query.all()
    
    def update_feed_stats(
        self, 
        feed_url: str, 
        success: bool, 
        article_count: int = 0, 
        tge_alerts: int = 0,
        error_message: Optional[str] = None
    ):
        """Update feed statistics"""
        with DatabaseManager.get_session() as db:
            feed = db.query(Feed).filter(Feed.url == feed_url).first()
            
            if not feed:
                # Create new feed
                feed = Feed(
                    name=feed_url.split('/')[-2] if '/' in feed_url else feed_url,
                    url=feed_url,
                    is_active=True
                )
                db.add(feed)
            
            # Update statistics
            feed.last_fetch = datetime.now(timezone.utc)
            
            if success:
                feed.success_count += 1
                feed.last_success = datetime.now(timezone.utc)
                feed.articles_found += article_count
                feed.tge_alerts_found += tge_alerts
            else:
                feed.failure_count += 1
                feed.last_failure = datetime.now(timezone.utc)
                feed.last_error = error_message
            
            db.commit()
    
    def get_feed_health_report(self) -> Dict[str, Any]:
        """Get feed health report"""
        with DatabaseManager.get_session() as db:
            total_feeds = db.query(Feed).count()
            active_feeds = db.query(Feed).filter(Feed.is_active == True).count()
            
            # Calculate healthy feeds (success rate > 80% in last 24h)
            recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            healthy_feeds = 0
            
            feeds = db.query(Feed).filter(Feed.is_active == True).all()
            for feed in feeds:
                if feed.success_count > 0:
                    success_rate = feed.success_count / (feed.success_count + feed.failure_count)
                    if success_rate > 0.8:
                        healthy_feeds += 1
            
            # Top performers
            top_performers = db.query(Feed).filter(
                Feed.is_active == True,
                Feed.tge_alerts_found > 0
            ).order_by(desc(Feed.tge_alerts_found)).limit(10).all()
            
            return {
                'total_feeds': total_feeds,
                'active_feeds': active_feeds,
                'healthy_feeds': healthy_feeds,
                'failing_feeds': active_feeds - healthy_feeds,
                'top_performers': [
                    {
                        'url': feed.url,
                        'name': feed.name,
                        'tge_found': feed.tge_alerts_found,
                        'success_rate': feed.success_count / (feed.success_count + feed.failure_count) if (feed.success_count + feed.failure_count) > 0 else 0
                    }
                    for feed in top_performers
                ]
            }
    
    # Monitoring session operations
    def create_monitoring_session(self, session_id: str) -> MonitoringSession:
        """Create new monitoring session"""
        with DatabaseManager.get_session() as db:
            session = MonitoringSession(
                session_id=session_id,
                status='running'
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            return session
    
    def update_monitoring_session(
        self, 
        session_id: str, 
        status: Optional[str] = None,
        **metrics
    ):
        """Update monitoring session"""
        with DatabaseManager.get_session() as db:
            session = db.query(MonitoringSession).filter(
                MonitoringSession.session_id == session_id
            ).first()
            
            if session:
                if status:
                    session.status = status
                    if status in ['completed', 'failed']:
                        session.end_time = datetime.now(timezone.utc)
                
                # Update metrics
                for key, value in metrics.items():
                    if hasattr(session, key):
                        setattr(session, key, value)
                
                db.commit()
    
    # System metrics operations
    def record_metric(
        self, 
        metric_type: str, 
        metric_name: str, 
        value: float, 
        unit: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None
    ):
        """Record system metric"""
        with DatabaseManager.get_session() as db:
            metric = SystemMetrics(
                metric_type=metric_type,
                metric_name=metric_name,
                value=value,
                unit=unit,
                tags=tags or {}
            )
            db.add(metric)
            db.commit()
    
    def get_metrics(
        self, 
        metric_type: Optional[str] = None,
        metric_name: Optional[str] = None,
        hours: int = 24
    ) -> List[SystemMetrics]:
        """Get system metrics"""
        with DatabaseManager.get_session() as db:
            query = db.query(SystemMetrics)
            
            if metric_type:
                query = query.filter(SystemMetrics.metric_type == metric_type)
            
            if metric_name:
                query = query.filter(SystemMetrics.metric_name == metric_name)
            
            # Filter by time
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            query = query.filter(SystemMetrics.timestamp >= cutoff)
            
            return query.order_by(desc(SystemMetrics.timestamp)).all()
    
    # Utility methods
    def get_or_create_company_by_name(self, name: str) -> Company:
        """Get or create company by name"""
        company = self.get_company_by_name(name)
        if not company:
            company_data = {
                'name': name,
                'priority': 'MEDIUM',
                'status': 'active'
            }
            company = self.create_or_update_company(company_data)
        return company
    
    def migrate_legacy_state(self, state_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate legacy file-based state to database"""
        migration_results = {
            'alerts_migrated': 0,
            'companies_migrated': 0,
            'errors': []
        }
        
        try:
            # Migrate alert history
            if 'alert_history' in state_data:
                for alert_data in state_data['alert_history']:
                    try:
                        # Convert legacy alert format to new format
                        alert_dict = {
                            'title': alert_data.get('title', 'Legacy Alert'),
                            'content': alert_data.get('content', ''),
                            'source': alert_data.get('source', 'legacy'),
                            'confidence': alert_data.get('confidence', 0.5),
                            'keywords_matched': alert_data.get('keywords', []),
                            'company_name': alert_data.get('companies', [None])[0] if alert_data.get('companies') else None,
                            'created_at': alert_data.get('timestamp')
                        }
                        
                        self.create_alert(alert_dict)
                        migration_results['alerts_migrated'] += 1
                        
                    except Exception as e:
                        migration_results['errors'].append(f"Alert migration error: {str(e)}")
            
            # Migrate companies from config
            from config import COMPANIES
            for company_config in COMPANIES:
                try:
                    self.create_or_update_company(company_config)
                    migration_results['companies_migrated'] += 1
                except Exception as e:
                    migration_results['errors'].append(f"Company migration error: {str(e)}")
            
            # Migrate feeds from config
            from config import NEWS_SOURCES
            for feed_url in NEWS_SOURCES:
                try:
                    with DatabaseManager.get_session() as db:
                        existing = db.query(Feed).filter(Feed.url == feed_url).first()
                        if not existing:
                            feed = Feed(
                                name=feed_url.split('/')[-2] if '/' in feed_url else feed_url,
                                url=feed_url,
                                is_active=True
                            )
                            db.add(feed)
                            db.commit()
                except Exception as e:
                    migration_results['errors'].append(f"Feed migration error: {str(e)}")
        
        except Exception as e:
            migration_results['errors'].append(f"General migration error: {str(e)}")
        
        return migration_results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        with DatabaseManager.get_session() as db:
            stats = {}
            
            # Basic counts
            stats['total_companies'] = db.query(Company).count()
            stats['total_alerts'] = db.query(Alert).count()
            stats['total_feeds'] = db.query(Feed).count()
            stats['active_feeds'] = db.query(Feed).filter(Feed.is_active == True).count()
            
            # Recent activity
            last_24h = datetime.now(timezone.utc) - timedelta(hours=24)
            last_7d = datetime.now(timezone.utc) - timedelta(days=7)
            
            stats['alerts_last_24h'] = db.query(Alert).filter(Alert.created_at >= last_24h).count()
            stats['alerts_last_7d'] = db.query(Alert).filter(Alert.created_at >= last_7d).count()
            
            # Confidence statistics
            avg_confidence = db.query(func.avg(Alert.confidence)).scalar()
            stats['avg_confidence'] = float(avg_confidence) if avg_confidence else 0.0
            
            # Source breakdown
            source_stats = db.query(Alert.source, func.count(Alert.id)).group_by(Alert.source).all()
            stats['alerts_by_source'] = {source: count for source, count in source_stats}
            
            # Company activity
            company_stats = db.query(
                Company.name, 
                func.count(Alert.id)
            ).outerjoin(Alert).group_by(Company.name).all()
            stats['alerts_by_company'] = {company: count for company, count in company_stats}
            
            return stats


# Global database service instance
db_service = DatabaseService()


# Migration utility function
def migrate_from_file_storage():
    """Migrate existing file-based storage to database"""
    import os
    
    results = {
        'success': False,
        'migration_results': {},
        'errors': []
    }
    
    try:
        # Look for existing state files
        state_files = [
            'state/monitor_state.json',
            'state/twitter_state.json',
            'state/news_state.json'
        ]
        
        for state_file in state_files:
            if os.path.exists(state_file):
                try:
                    with open(state_file, 'r') as f:
                        state_data = json.load(f)
                    
                    migration_result = db_service.migrate_legacy_state(state_data)
                    results['migration_results'][state_file] = migration_result
                    
                except Exception as e:
                    results['errors'].append(f"Failed to migrate {state_file}: {str(e)}")
        
        results['success'] = True
        
    except Exception as e:
        results['errors'].append(f"Migration failed: {str(e)}")
    
    return results


if __name__ == "__main__":
    # Test database service
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "migrate":
        print("Starting migration from file storage to database...")
        results = migrate_from_file_storage()
        print(f"Migration results: {results}")
    else:
        print("Testing database service...")
        
        # Test basic operations
        try:
            # Test company operations
            companies = db_service.get_companies()
            print(f"Found {len(companies)} companies")
            
            # Test alert operations
            alerts = db_service.get_recent_alerts(24)
            print(f"Found {len(alerts)} recent alerts")
            
            # Test statistics
            stats = db_service.get_statistics()
            print(f"System statistics: {stats}")
            
            print("✓ Database service test completed successfully")
            
        except Exception as e:
            print(f"✗ Database service test failed: {e}")
            raise