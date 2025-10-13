"""
Optimized News Scraper for TGE Detection
Enhanced with full article content extraction, parallel processing, and smart prioritization
"""

import os
import json
import feedparser
import requests
import logging
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, urljoin
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
from collections import defaultdict
import re
from bs4 import BeautifulSoup
from newspaper import Article
import nltk

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Download required NLTK data for article extraction
# Use timeout and non-blocking mode to prevent initialization hang
def _download_nltk_data():
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        try:
            nltk.download('punkt', quiet=True, raise_on_error=True)
        except Exception as e:
            logger.warning(f"NLTK punkt download failed (non-critical): {e}")

# Run in background to avoid blocking
import threading
nltk_thread = threading.Thread(target=_download_nltk_data, daemon=True)
nltk_thread.start()


class OptimizedNewsScraper:
    """Enhanced news scraper with full article extraction and intelligent processing."""

    def __init__(self, companies: List[Dict], keywords: List[str], news_sources: List[str],
                 relevance_threshold: float = 0.65, min_confidence: float = 0.60):
        self.companies = companies
        self.keywords = keywords
        self.news_sources = news_sources
        self.relevance_threshold = relevance_threshold
        self.min_confidence = min_confidence

        # Swarm coordination hooks (optional, set via set_swarm_hooks)
        self.swarm_hooks = None
        
        # State management
        self.state_file = 'state/news_state.json'
        self.cache_file = 'state/article_cache.json'
        self.state = self.load_state()
        self.cache = self.load_cache()
        
        # Performance tracking
        self.feed_stats = self.state.get('feed_stats', {})
        self.session = self._create_session()
        
        # Article extraction patterns
        self.article_patterns = {
            'medium.com': self._extract_medium_article,
            'mirror.xyz': self._extract_mirror_article,
            'substack.com': self._extract_substack_article,
            'ghost.io': self._extract_ghost_article
        }
        
        # Compile regex patterns
        self.url_normalizers = self._compile_url_normalizers()
        self.content_cleaners = self._compile_content_cleaners()

    def set_swarm_hooks(self, swarm_hooks):
        """Set swarm coordination hooks for multi-agent coordination."""
        self.swarm_hooks = swarm_hooks
        logger.info("Swarm hooks enabled for news scraper")
        
    def load_state(self) -> Dict:
        """Load persistent state with feed statistics."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading state: {str(e)}")
        
        return {
            'seen_urls': {},
            'feed_stats': {},
            'last_full_scan': None,
            'failed_feeds': {},
            'article_fetch_stats': {}
        }
    
    def load_cache(self) -> Dict:
        """Load article content cache."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                    # Clean old entries (>3 days)
                    cutoff = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
                    cache['articles'] = {k: v for k, v in cache.get('articles', {}).items() 
                                       if v.get('cached_at', '') > cutoff}
                    return cache
        except Exception as e:
            logger.error(f"Error loading cache: {str(e)}")
        
        return {'articles': {}, 'summaries': {}}
    
    def save_state(self):
        """Save persistent state."""
        try:
            os.makedirs('state', exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state: {str(e)}")
    
    def save_cache(self):
        """Save article cache."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cache: {str(e)}")
    
    def _create_session(self) -> requests.Session:
        """Create optimized requests session."""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; TGEMonitor/1.0; +https://example.com/bot)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })
        
        # Increase connection pool size
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=20,
            pool_maxsize=20,
            max_retries=requests.adapters.Retry(
                total=3,
                backoff_factor=0.3,
                status_forcelist=[500, 502, 503, 504]
            )
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        return session
    
    def _compile_url_normalizers(self) -> Dict[str, callable]:
        """Compile URL normalization patterns."""
        return {
            'medium.com': lambda url: re.sub(r'\?.*$', '', url),
            'mirror.xyz': lambda url: re.sub(r'\?.*$', '', url),
            'twitter.com': lambda url: url.replace('twitter.com', 'x.com'),
            'x.com': lambda url: url
        }
    
    def _compile_content_cleaners(self) -> Dict[str, re.Pattern]:
        """Compile content cleaning patterns."""
        return {
            'script_tags': re.compile(r'<script.*?</script>', re.DOTALL | re.IGNORECASE),
            'style_tags': re.compile(r'<style.*?</style>', re.DOTALL | re.IGNORECASE),
            'html_tags': re.compile(r'<[^>]+>'),
            'extra_spaces': re.compile(r'\s+'),
            'urls': re.compile(r'https?://\S+'),
        }
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Apply domain-specific normalizers
        for pattern, normalizer in self.url_normalizers.items():
            if pattern in domain:
                return normalizer(url)
        
        # Default normalization
        return url.rstrip('/')
    
    def fetch_article_content(self, url: str) -> Optional[str]:
        """Fetch and extract full article content."""
        # Check swarm shared cache first (if enabled)
        if self.swarm_hooks and self.swarm_hooks.enabled:
            cache_key = hashlib.sha256(url.encode()).hexdigest()
            swarm_cached = self.swarm_hooks.check_duplicate(f"article_{cache_key}")
            if swarm_cached:
                logger.debug(f"Using swarm cached content for: {url}")
                # Try to retrieve from swarm memory
                cached_content = self.swarm_hooks.memory_retrieve(f"articles/{cache_key}", shared=True)
                if cached_content:
                    return cached_content

        # Check local cache
        cache_key = hashlib.sha256(url.encode()).hexdigest()
        if cache_key in self.cache['articles']:
            logger.debug(f"Using cached content for: {url}")
            return self.cache['articles'][cache_key]['content']
        
        try:
            # Use newspaper3k for general article extraction
            article = Article(url)
            article.download()
            article.parse()
            
            # Get the main content
            content = article.text
            
            # If content is too short, try custom extractors
            if len(content) < 200:
                domain = urlparse(url).netloc.lower()
                for pattern, extractor in self.article_patterns.items():
                    if pattern in domain:
                        custom_content = extractor(url)
                        if custom_content and len(custom_content) > len(content):
                            content = custom_content
            
            # Clean content
            content = self.clean_article_content(content)
            
            # Cache the result locally
            if content and len(content) > 100:
                self.cache['articles'][cache_key] = {
                    'content': content,
                    'cached_at': datetime.now(timezone.utc).isoformat(),
                    'length': len(content)
                }
                self.save_cache()

                # Also cache in swarm shared memory (if enabled)
                if self.swarm_hooks and self.swarm_hooks.enabled:
                    self.swarm_hooks.coordinate_deduplication(
                        f"article_{cache_key}",
                        {
                            'url': url,
                            'cached_at': datetime.now(timezone.utc).isoformat(),
                            'length': len(content)
                        }
                    )
                    # Store content in shared memory for other agents
                    self.swarm_hooks.memory_store(
                        f"articles/{cache_key}",
                        content[:5000],  # Store first 5000 chars
                        ttl=3600,
                        shared=True
                    )

                    # Post-edit hook to notify other agents
                    self.swarm_hooks.post_edit(
                        f"article_cache/{cache_key}",
                        operation="create",
                        memory_key=f"swarm/shared/articles/{cache_key}"
                    )

            return content
            
        except Exception as e:
            logger.debug(f"Error fetching article {url}: {str(e)}")
            return None
    
    def _extract_medium_article(self, url: str) -> Optional[str]:
        """Custom extractor for Medium articles."""
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find article content
            article_tags = soup.find_all(['article', 'main'])
            if article_tags:
                # Extract paragraphs
                paragraphs = []
                for tag in article_tags:
                    for p in tag.find_all(['p', 'h1', 'h2', 'h3']):
                        text = p.get_text(strip=True)
                        if text and len(text) > 20:
                            paragraphs.append(text)
                
                return '\n'.join(paragraphs)
        except Exception as e:
            logger.debug(f"Medium extraction failed: {str(e)}")
        
        return None
    
    def _extract_mirror_article(self, url: str) -> Optional[str]:
        """Custom extractor for Mirror.xyz articles."""
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find main content div
            content_div = soup.find('div', {'class': re.compile(r'prose', re.I)})
            if content_div:
                return content_div.get_text(separator='\n', strip=True)
        except Exception as e:
            logger.debug(f"Mirror extraction failed: {str(e)}")
        
        return None
    
    def _extract_substack_article(self, url: str) -> Optional[str]:
        """Custom extractor for Substack articles."""
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find post content
            content_div = soup.find('div', {'class': 'post-content'})
            if content_div:
                return content_div.get_text(separator='\n', strip=True)
        except Exception as e:
            logger.debug(f"Substack extraction failed: {str(e)}")
        
        return None
    
    def _extract_ghost_article(self, url: str) -> Optional[str]:
        """Custom extractor for Ghost blog articles."""
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find post content
            content = soup.find(['article', 'main', 'div'], {'class': re.compile(r'post-content|article-content', re.I)})
            if content:
                return content.get_text(separator='\n', strip=True)
        except Exception as e:
            logger.debug(f"Ghost extraction failed: {str(e)}")
        
        return None
    
    def clean_article_content(self, content: str) -> str:
        """Clean and normalize article content."""
        if not content:
            return ""
        
        # Remove extra whitespace
        content = self.content_cleaners['extra_spaces'].sub(' ', content)
        
        # Remove very short lines (likely navigation elements)
        lines = content.split('\n')
        cleaned_lines = [line.strip() for line in lines if len(line.strip()) > 30]
        
        return '\n'.join(cleaned_lines)
    
    def analyze_content_relevance(self, content: str, title: str = "") -> Tuple[bool, float, Dict]:
        """Analyze article content for TGE relevance with NLP techniques."""
        relevance_info = {
            'matched_companies': [],
            'matched_keywords': [],
            'confidence': 0,
            'signals': [],
            'context_snippets': []
        }
        
        # Combine title and content for analysis
        full_text = f"{title}\n{content}".lower()
        
        # Company detection with context
        for company in self.companies:
            company_pattern = re.compile(
                r'\b(' + '|'.join(re.escape(term.lower()) for term in 
                                [company['name']] + company.get('aliases', [])) + r')\b',
                re.IGNORECASE
            )
            
            matches = list(company_pattern.finditer(full_text))
            if matches:
                relevance_info['matched_companies'].append(company['name'])
                relevance_info['confidence'] += 25
                
                # Extract context around company mentions
                for match in matches[:3]:  # First 3 mentions
                    start = max(0, match.start() - 100)
                    end = min(len(full_text), match.end() + 100)
                    snippet = full_text[start:end].strip()
                    relevance_info['context_snippets'].append(snippet)
        
        # Enhanced keyword matching with weighted scoring
        high_value_phrases = [
            (r'token generation event', 45),
            (r'tge\s+(is\s+)?live', 40),
            (r'airdrop\s+(is\s+)?live', 40),
            (r'claim\s+(your\s+)?tokens?\s+(now|today)', 40),
            (r'token\s+launch\s+date', 35),
            (r'tokens?\s+(are\s+)?(now\s+)?available', 35),
            (r'trading\s+(is\s+)?(now\s+)?live', 35),
            (r'claim\s+portal\s+(is\s+)?(now\s+)?live', 40),
            (r'genesis\s+event', 30),
            (r'mainnet\s+launch', 30)
        ]

        for phrase_pattern, score in high_value_phrases:
            matches = re.finditer(phrase_pattern, full_text, re.IGNORECASE)
            for match in matches:
                relevance_info['matched_keywords'].append(match.group(0))
                relevance_info['confidence'] += score
                relevance_info['signals'].append('high_value_phrase')
                break  # Count each pattern only once

        # General keyword matching (from self.keywords)
        for keyword in self.keywords:
            keyword_pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            if re.search(keyword_pattern, full_text):
                relevance_info['matched_keywords'].append(keyword)
                # Lower confidence for general keywords vs high-value phrases
                relevance_info['confidence'] += 15

        # Token symbol detection
        token_patterns = re.findall(r'\$[A-Z]{2,10}\b', content)
        if token_patterns:
            # Check if any match company tokens
            for company in self.companies:
                for token in company.get('tokens', []):
                    if f"${token}" in token_patterns:
                        relevance_info['confidence'] += 25
                        relevance_info['signals'].append(f'token_symbol_{token}')
        
        # Date proximity analysis
        date_patterns = [
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}',
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\b(next|this)\s+(week|month)',
            r'\bQ[1-4]\s*2024',
            r'\b(today|tomorrow|soon)\b'
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, full_text, re.IGNORECASE):
                relevance_info['signals'].append('date_mentioned')
                relevance_info['confidence'] += 10
                break
        
        # Enhanced exclusion patterns with context awareness
        exclusions = [
            (r'test\s*net(?!\s+to\s+mainnet)', 50, 'testnet'),  # Don't penalize "testnet to mainnet"
            (r'game\s+token(?!omics)', 40, 'game_token'),  # Don't penalize "game tokenomics"
            (r'nft\s+(collection|drop|mint)', 30, 'nft_collection'),
            (r'price\s+prediction', 35, 'speculation'),
            (r'technical\s+analysis', 35, 'speculation'),
            (r'espresso\s+machine', 60, 'coffee_machine'),
            (r'coffee\s+(shop|bean|brew)', 50, 'coffee_related'),
            (r'in-game\s+(currency|item|token)', 45, 'gaming'),
            (r'play-to-earn\s+game', 40, 'gaming'),
            (r'fabric\s+(textile|cloth|material)', 50, 'physical_goods')
        ]

        # Check for crypto context
        crypto_terms = [
            'blockchain', 'crypto', 'defi', 'web3', 'protocol', 'mainnet',
            'smart contract', 'dapp', 'layer 2', 'rollup'
        ]
        has_crypto_context = any(term in full_text for term in crypto_terms)

        for pattern, penalty, label in exclusions:
            if re.search(pattern, full_text, re.IGNORECASE):
                # Reduce penalty if crypto context present
                actual_penalty = penalty // 2 if has_crypto_context else penalty
                relevance_info['confidence'] -= actual_penalty
                relevance_info['signals'].append(f'exclusion:{label}')
        
        # Context window analysis
        if relevance_info['matched_companies'] and relevance_info['matched_keywords']:
            # Check if company and keywords appear near each other
            for company in relevance_info['matched_companies']:
                company_pattern = re.escape(company.lower())
                for keyword in relevance_info['matched_keywords']:
                    keyword_pattern = re.escape(keyword.lower())
                    
                    # Find positions
                    company_pos = [m.start() for m in re.finditer(company_pattern, full_text)]
                    keyword_pos = [m.start() for m in re.finditer(keyword_pattern, full_text)]
                    
                    # Check proximity (within 200 characters)
                    for cp in company_pos:
                        for kp in keyword_pos:
                            if abs(cp - kp) < 200:
                                relevance_info['confidence'] += 20
                                relevance_info['signals'].append('proximity_match')
                                break
        
        # Normalize confidence
        relevance_info['confidence'] = max(0, min(100, relevance_info['confidence']))

        # Apply relevance threshold
        confidence_score = relevance_info['confidence'] / 100
        is_relevant = confidence_score >= self.relevance_threshold

        # Add metadata about threshold
        relevance_info['threshold_used'] = self.relevance_threshold
        relevance_info['meets_threshold'] = is_relevant

        return is_relevant, confidence_score, relevance_info
    
    def process_feed(self, feed_url: str) -> List[Dict]:
        """Process a single RSS feed with article content extraction."""
        articles = []
        
        try:
            # Update feed statistics
            feed_key = hashlib.md5(feed_url.encode()).hexdigest()
            if feed_key not in self.feed_stats:
                self.feed_stats[feed_key] = {
                    'url': feed_url,
                    'success_count': 0,
                    'failure_count': 0,
                    'tge_found': 0,
                    'last_success': None
                }
            
            # Fetch and parse feed
            response = self.session.get(feed_url, timeout=10)
            feed = feedparser.parse(response.content)
            
            if feed.bozo:
                raise Exception(f"Feed parsing error: {feed.bozo_exception}")
            
            # Process entries
            entries_processed = 0
            for entry in feed.entries[:50]:  # Limit entries per feed
                try:
                    # Extract basic info
                    url = self.normalize_url(entry.get('link', ''))
                    if not url or url in self.state['seen_urls']:
                        continue
                    
                    title = entry.get('title', '')
                    summary = entry.get('summary', '')
                    published = entry.get('published_parsed')
                    
                    # Quick relevance check on title/summary
                    quick_text = f"{title} {summary}".lower()
                    has_potential = any(keyword in quick_text for keyword in self.keywords[:20])
                    
                    if not has_potential:
                        # Skip articles that clearly aren't relevant
                        continue
                    
                    # Fetch full article content
                    content = self.fetch_article_content(url)
                    
                    if content:
                        # Analyze full content
                        is_relevant, confidence, info = self.analyze_content_relevance(content, title)

                        # Apply minimum confidence threshold
                        if is_relevant and confidence >= self.min_confidence:
                            articles.append({
                                'url': url,
                                'title': title,
                                'summary': summary[:500],
                                'content': content[:2000],  # Store first 2000 chars
                                'published': published,
                                'source': feed_url,
                                'confidence': confidence,
                                'relevance_info': info,
                                'feed_title': feed.feed.get('title', 'Unknown'),
                                'meets_min_confidence': True
                            })

                            # Update stats
                            self.feed_stats[feed_key]['tge_found'] += 1
                    
                    # Mark as seen
                    self.state['seen_urls'][url] = datetime.now(timezone.utc).isoformat()
                    entries_processed += 1
                    
                except Exception as e:
                    logger.debug(f"Error processing entry: {str(e)}")
                    continue
            
            # Update success stats
            self.feed_stats[feed_key]['success_count'] += 1
            self.feed_stats[feed_key]['last_success'] = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"Processed {entries_processed} entries from {feed.feed.get('title', feed_url)}")
            
        except Exception as e:
            logger.error(f"Error processing feed {feed_url}: {str(e)}")
            self.feed_stats[feed_key]['failure_count'] += 1
        
        return articles
    
    def prioritize_feeds(self) -> List[str]:
        """Prioritize feeds based on historical performance."""
        feed_scores = []
        
        for feed_url in self.news_sources:
            feed_key = hashlib.md5(feed_url.encode()).hexdigest()
            stats = self.feed_stats.get(feed_key, {})
            
            # Calculate score based on success rate and TGE discovery rate
            total_attempts = stats.get('success_count', 0) + stats.get('failure_count', 0)
            if total_attempts > 0:
                success_rate = stats.get('success_count', 0) / total_attempts
                tge_rate = stats.get('tge_found', 0) / max(stats.get('success_count', 1), 1)
                
                # Weight TGE discovery rate higher
                score = (success_rate * 0.3) + (tge_rate * 0.7)
            else:
                score = 0.5  # Default score for new feeds
            
            feed_scores.append((feed_url, score))
        
        # Sort by score (descending)
        feed_scores.sort(key=lambda x: x[1], reverse=True)
        
        return [feed[0] for feed in feed_scores]
    
    def fetch_all_articles(self, timeout: int = 120) -> List[Dict]:
        """Fetch articles from all sources with parallel processing."""
        all_articles = []
        start_time = time.time()
        
        # Prioritize feeds
        prioritized_feeds = self.prioritize_feeds()
        
        # Process feeds in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit feed processing tasks
            future_to_feed = {
                executor.submit(self.process_feed, feed): feed 
                for feed in prioritized_feeds
            }
            
            # Process results as they complete
            for future in as_completed(future_to_feed):
                if time.time() - start_time > timeout:
                    logger.warning("Timeout reached, stopping feed processing")
                    break
                
                feed = future_to_feed[future]
                try:
                    articles = future.result(timeout=30)
                    all_articles.extend(articles)
                    logger.info(f"Found {len(articles)} relevant articles from {feed}")
                except FuturesTimeoutError:
                    logger.warning(f"Feed timeout: {feed}")
                except Exception as e:
                    logger.error(f"Error processing feed {feed}: {str(e)}")
        
        # Save state
        self.state['feed_stats'] = self.feed_stats
        self.state['last_full_scan'] = datetime.now(timezone.utc).isoformat()
        self.save_state()
        
        # Sort by confidence and recency
        all_articles.sort(key=lambda x: (x['confidence'], x.get('published', '')), reverse=True)
        
        logger.info(f"Total relevant articles found: {len(all_articles)}")
        return all_articles
    
    def get_feed_health_report(self) -> Dict:
        """Generate health report for all feeds."""
        report = {
            'total_feeds': len(self.news_sources),
            'healthy_feeds': 0,
            'failing_feeds': 0,
            'top_performers': [],
            'needs_attention': []
        }
        
        for feed_url in self.news_sources:
            feed_key = hashlib.md5(feed_url.encode()).hexdigest()
            stats = self.feed_stats.get(feed_key, {})
            
            total_attempts = stats.get('success_count', 0) + stats.get('failure_count', 0)
            if total_attempts > 5:  # Need sufficient data
                success_rate = stats.get('success_count', 0) / total_attempts
                
                if success_rate > 0.8:
                    report['healthy_feeds'] += 1
                    if stats.get('tge_found', 0) > 0:
                        report['top_performers'].append({
                            'url': stats.get('url', feed_url),
                            'tge_found': stats.get('tge_found', 0),
                            'success_rate': success_rate
                        })
                elif success_rate < 0.5:
                    report['failing_feeds'] += 1
                    report['needs_attention'].append({
                        'url': stats.get('url', feed_url),
                        'failure_rate': 1 - success_rate,
                        'last_success': stats.get('last_success')
                    })
        
        return report