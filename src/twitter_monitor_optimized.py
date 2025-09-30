"""
Optimized Twitter Monitor for TGE Detection
Enhanced with rate limit management, batch operations, and advanced search strategies
"""

import os
import json
import tweepy
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
import time
from threading import Lock
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OptimizedTwitterMonitor:
    """Enhanced Twitter monitoring with rate limit management and batch operations."""
    
    def __init__(self, bearer_token: str, companies: List[Dict], keywords: List[str]):
        self.bearer_token = bearer_token
        self.companies = companies
        self.keywords = keywords
        self.client = None
        self.state_file = 'state/twitter_state.json'
        self.cache_file = 'state/twitter_cache.json'
        self.state = self.load_state()
        self.cache = self.load_cache()
        self.rate_limits = defaultdict(dict)
        self.rate_limit_lock = Lock()
        
        # Initialize Twitter client
        self._init_client()
        
        # Compile regex patterns for better matching
        self.token_pattern = re.compile(r'\$[A-Z]{2,10}\b')  # Match $TOKEN patterns
        self.company_patterns = self._compile_company_patterns()
        
    def _init_client(self):
        """Initialize Twitter API v2 client with error handling."""
        try:
            self.client = tweepy.Client(bearer_token=self.bearer_token, wait_on_rate_limit=True)
            logger.info("Twitter client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter client: {str(e)}")
            raise
            
    def _compile_company_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for company matching."""
        patterns = {}
        for company in self.companies:
            # Create pattern with company name and aliases
            terms = [company['name']] + company.get('aliases', [])
            # Escape special characters and create case-insensitive pattern
            escaped_terms = [re.escape(term) for term in terms]
            pattern = '|'.join(escaped_terms)
            patterns[company['name']] = re.compile(pattern, re.IGNORECASE)
        return patterns
    
    def load_state(self) -> Dict:
        """Load persistent state with enhanced structure."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading state: {str(e)}")
        
        return {
            'since_ids': {},
            'user_id_cache': {},
            'list_id': None,
            'last_full_scan': None,
            'rate_limit_resets': {},
            'failed_accounts': {}
        }
    
    def load_cache(self) -> Dict:
        """Load tweet cache for deduplication."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                    # Clean old entries (>7 days)
                    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
                    cache['tweets'] = {k: v for k, v in cache.get('tweets', {}).items() 
                                     if v.get('timestamp', '') > cutoff}
                    return cache
        except Exception as e:
            logger.error(f"Error loading cache: {str(e)}")
        
        return {'tweets': {}, 'similar_tweets': {}}
    
    def save_state(self):
        """Save persistent state."""
        try:
            os.makedirs('state', exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state: {str(e)}")
    
    def save_cache(self):
        """Save tweet cache."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cache: {str(e)}")
    
    def check_rate_limit(self, endpoint: str) -> bool:
        """Check if we can make a request to the given endpoint."""
        with self.rate_limit_lock:
            limit_info = self.rate_limits.get(endpoint, {})
            reset_time = limit_info.get('reset', 0)
            remaining = limit_info.get('remaining', 1)
            
            if remaining <= 0 and time.time() < reset_time:
                wait_time = reset_time - time.time()
                logger.warning(f"Rate limit reached for {endpoint}. Waiting {wait_time:.0f}s")
                return False
            return True
    
    def update_rate_limit(self, endpoint: str, response):
        """Update rate limit information from API response."""
        if hasattr(response, 'headers'):
            with self.rate_limit_lock:
                headers = response.headers
                self.rate_limits[endpoint] = {
                    'limit': int(headers.get('x-rate-limit-limit', 100)),
                    'remaining': int(headers.get('x-rate-limit-remaining', 1)),
                    'reset': int(headers.get('x-rate-limit-reset', time.time() + 900))
                }
    
    def batch_lookup_users(self, handles: List[str]) -> Dict[str, str]:
        """Batch lookup user IDs to minimize API calls."""
        user_map = {}
        handles_to_lookup = []
        
        # Check cache first
        for handle in handles:
            clean_handle = handle.strip('@')
            if clean_handle in self.state['user_id_cache']:
                user_map[handle] = self.state['user_id_cache'][clean_handle]
            else:
                handles_to_lookup.append(clean_handle)
        
        # Batch lookup remaining users (up to 100 per request)
        if handles_to_lookup:
            try:
                for i in range(0, len(handles_to_lookup), 100):
                    batch = handles_to_lookup[i:i+100]
                    users = self.client.get_users(usernames=batch)
                    
                    if users.data:
                        for user in users.data:
                            user_map[f"@{user.username}"] = user.id
                            self.state['user_id_cache'][user.username] = user.id
                    
                    # Small delay to avoid hitting rate limits
                    time.sleep(0.1)
                    
                self.save_state()
            except Exception as e:
                logger.error(f"Error in batch user lookup: {str(e)}")
        
        return user_map
    
    def create_or_update_list(self, user_ids: List[str]) -> Optional[str]:
        """Create or update a Twitter list for efficient timeline monitoring."""
        try:
            list_id = self.state.get('list_id')
            
            # Create list if it doesn't exist
            if not list_id:
                # Get authenticated user ID
                me = self.client.get_me()
                if me.data:
                    list_response = self.client.create_list(
                        name="TGE_Monitor_List",
                        description="Automated list for TGE monitoring",
                        private=True
                    )
                    if list_response.data:
                        list_id = list_response.data['id']
                        self.state['list_id'] = list_id
                        self.save_state()
            
            # Add members to list
            if list_id:
                # Twitter allows adding up to 100 members at once
                for i in range(0, len(user_ids), 100):
                    batch = user_ids[i:i+100]
                    try:
                        self.client.add_list_member(id=list_id, user_id=batch)
                        time.sleep(0.5)
                    except Exception as e:
                        logger.error(f"Error adding members to list: {str(e)}")
                
                return list_id
                
        except Exception as e:
            logger.error(f"Error managing Twitter list: {str(e)}")
        
        return None
    
    def search_tge_tweets(self) -> List[Dict]:
        """Enhanced search for TGE-related tweets with smart query construction."""
        tweets = []
        
        # Group companies by priority
        high_priority = [c for c in self.companies if c.get('priority') == 'HIGH']
        other_companies = [c for c in self.companies if c.get('priority') != 'HIGH']
        
        # Search strategies
        search_queries = []
        
        # Strategy 1: High-priority companies with strong TGE keywords
        if high_priority:
            company_terms = []
            for company in high_priority[:5]:  # Limit to avoid query length issues
                terms = [f'"{company["name"]}"'] + [f'"{alias}"' for alias in company.get('aliases', [])]
                company_terms.append(f"({' OR '.join(terms)})")
            
            tge_terms = '("TGE" OR "token launch" OR "token generation event" OR "airdrop live")'
            query = f"({' OR '.join(company_terms)}) {tge_terms} -is:retweet lang:en"
            search_queries.append(query)
        
        # Strategy 2: Token symbol mentions with action words
        token_symbols = []
        for company in self.companies:
            for token in company.get('tokens', []):
                if token and len(token) >= 2:
                    token_symbols.append(f"${token}")
        
        if token_symbols:
            symbols_query = f"({' OR '.join(token_symbols[:10])}) (launching OR live OR airdrop OR trading)"
            search_queries.append(f"{symbols_query} -is:retweet lang:en")
        
        # Strategy 3: Generic TGE announcements from key accounts
        key_accounts = ["@CoinList", "@BinanceLabs", "@a16zcrypto", "@multicoincap"]
        announcer_query = f'({" OR ".join(key_accounts)}) ("TGE" OR "token launch" OR "token sale")'
        search_queries.append(f"{announcer_query} -is:retweet lang:en")
        
        # Execute searches
        for query in search_queries[:3]:  # Limit to avoid rate limits
            try:
                if not self.check_rate_limit('search'):
                    continue
                
                logger.info(f"Searching: {query[:100]}...")
                search_results = self.client.search_recent_tweets(
                    query=query,
                    max_results=50,
                    tweet_fields=['created_at', 'author_id', 'public_metrics', 'entities']
                )
                
                if search_results.data:
                    for tweet in search_results.data:
                        # Check if we've seen this tweet
                        if tweet.id not in self.cache['tweets']:
                            tweets.append({
                                'id': tweet.id,
                                'text': tweet.text,
                                'author_id': tweet.author_id,
                                'created_at': tweet.created_at,
                                'metrics': tweet.public_metrics,
                                'url': f"https://twitter.com/i/web/status/{tweet.id}",
                                'search_strategy': 'advanced_search'
                            })
                            # Cache the tweet
                            self.cache['tweets'][tweet.id] = {
                                'timestamp': datetime.now(timezone.utc).isoformat(),
                                'text_hash': hash(tweet.text)
                            }
                
                # Small delay between searches
                time.sleep(1)
                
            except tweepy.TooManyRequests:
                logger.warning("Rate limit hit during search")
                break
            except Exception as e:
                logger.error(f"Error in search: {str(e)}")
        
        self.save_cache()
        return tweets
    
    def monitor_list_timeline(self, list_id: str) -> List[Dict]:
        """Monitor Twitter list timeline for efficiency."""
        tweets = []
        
        try:
            since_id = self.state['since_ids'].get(f'list_{list_id}')
            
            # Get list timeline
            list_tweets = self.client.get_list_tweets(
                id=list_id,
                max_results=100,
                since_id=since_id,
                tweet_fields=['created_at', 'author_id', 'public_metrics', 'entities']
            )
            
            if list_tweets.data:
                newest_id = max(tweet.id for tweet in list_tweets.data)
                self.state['since_ids'][f'list_{list_id}'] = newest_id
                
                for tweet in list_tweets.data:
                    if tweet.id not in self.cache['tweets']:
                        tweets.append({
                            'id': tweet.id,
                            'text': tweet.text,
                            'author_id': tweet.author_id,
                            'created_at': tweet.created_at,
                            'metrics': tweet.public_metrics,
                            'url': f"https://twitter.com/i/web/status/{tweet.id}",
                            'source': 'list_timeline'
                        })
                        self.cache['tweets'][tweet.id] = {
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }
                
                self.save_state()
                
        except Exception as e:
            logger.error(f"Error monitoring list: {str(e)}")
        
        return tweets
    
    def analyze_tweet_relevance(self, tweet: Dict) -> Tuple[bool, float, Dict]:
        """Enhanced tweet analysis with confidence scoring."""
        text = tweet['text'].lower()
        relevance_info = {
            'matched_companies': [],
            'matched_keywords': [],
            'token_symbols': [],
            'confidence': 0,
            'signals': []
        }
        
        # Check for token symbols
        token_matches = self.token_pattern.findall(tweet['text'])
        if token_matches:
            relevance_info['token_symbols'] = token_matches
            relevance_info['confidence'] += 20
            relevance_info['signals'].append('token_symbol')
        
        # Check for company mentions
        for company in self.companies:
            pattern = self.company_patterns[company['name']]
            if pattern.search(text):
                relevance_info['matched_companies'].append(company['name'])
                relevance_info['confidence'] += 30
                
                # Check if company tokens are mentioned
                for token in company.get('tokens', []):
                    if f"${token.upper()}" in token_matches:
                        relevance_info['confidence'] += 20
                        relevance_info['signals'].append('company_token_match')
        
        # Check for TGE keywords with weighted scoring
        high_confidence_keywords = ['tge', 'token generation event', 'token launch', 
                                  'airdrop live', 'claim airdrop', 'token is live']
        medium_confidence_keywords = ['mainnet launch', 'tokenomics', 'token sale', 
                                    'listing', 'trading live']
        
        for keyword in high_confidence_keywords:
            if keyword in text:
                relevance_info['matched_keywords'].append(keyword)
                relevance_info['confidence'] += 25
                relevance_info['signals'].append('high_confidence_keyword')
        
        for keyword in medium_confidence_keywords:
            if keyword in text:
                relevance_info['matched_keywords'].append(keyword)
                relevance_info['confidence'] += 15
                relevance_info['signals'].append('medium_confidence_keyword')
        
        # Check engagement metrics for viral potential
        metrics = tweet.get('metrics', {})
        if metrics:
            engagement_rate = (metrics.get('retweet_count', 0) + 
                             metrics.get('like_count', 0)) / max(metrics.get('impression_count', 1), 1)
            if engagement_rate > 0.05:  # 5% engagement rate
                relevance_info['confidence'] += 10
                relevance_info['signals'].append('high_engagement')
        
        # Apply exclusion patterns
        exclusions = ['test', 'testnet', 'game token', 'nft', 'analysis', 'prediction']
        for exclusion in exclusions:
            if exclusion in text:
                relevance_info['confidence'] -= 20
                relevance_info['signals'].append(f'exclusion_{exclusion}')
        
        # Normalize confidence score
        relevance_info['confidence'] = max(0, min(100, relevance_info['confidence']))
        
        # Determine if relevant (threshold: 40%)
        is_relevant = relevance_info['confidence'] >= 40
        
        return is_relevant, relevance_info['confidence'] / 100, relevance_info
    
    def fetch_all_tweets(self, timeout: int = 60) -> List[Dict]:
        """Fetch tweets with improved efficiency and error handling."""
        all_tweets = []
        start_time = time.time()
        
        try:
            # Step 1: Get user IDs efficiently
            handles = list(set(TWITTER_ACCOUNTS))  # Remove duplicates
            user_map = self.batch_lookup_users(handles)
            
            # Step 2: Create/update list for efficient monitoring
            user_ids = list(user_map.values())
            list_id = self.create_or_update_list(user_ids) if user_ids else None
            
            # Step 3: Use parallel execution for different strategies
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = []
                
                # List timeline monitoring (most efficient)
                if list_id:
                    futures.append(executor.submit(self.monitor_list_timeline, list_id))
                
                # Advanced search queries
                futures.append(executor.submit(self.search_tge_tweets))
                
                # Process results as they complete
                for future in futures:
                    remaining_time = timeout - (time.time() - start_time)
                    if remaining_time <= 0:
                        break
                    
                    try:
                        tweets = future.result(timeout=remaining_time)
                        all_tweets.extend(tweets)
                    except FuturesTimeoutError:
                        logger.warning("Operation timed out")
                    except Exception as e:
                        logger.error(f"Error fetching tweets: {str(e)}")
            
            # Deduplicate tweets
            seen_ids = set()
            unique_tweets = []
            for tweet in all_tweets:
                if tweet['id'] not in seen_ids:
                    seen_ids.add(tweet['id'])
                    unique_tweets.append(tweet)
            
            logger.info(f"Fetched {len(unique_tweets)} unique tweets in {time.time() - start_time:.1f}s")
            return unique_tweets
            
        except Exception as e:
            logger.error(f"Error in fetch_all_tweets: {str(e)}")
            return []


# Import Twitter accounts from config
try:
    from config import TWITTER_ACCOUNTS
except ImportError:
    TWITTER_ACCOUNTS = []
    logger.warning("Could not import TWITTER_ACCOUNTS from config")