import os
import re
import json
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime
from urllib.parse import quote_plus

import tweepy
from tweepy.errors import TooManyRequests, HTTPException

from config import COMPANIES, TGE_KEYWORDS, HIGH_CONFIDENCE_TGE_KEYWORDS, MEDIUM_CONFIDENCE_TGE_KEYWORDS

# ------------------ persistent since_id per user/search ------------------

STATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state")
SINCE_PATH = os.path.join(STATE_DIR, "twitter_since.json")


def _load_since_map() -> dict:
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        if os.path.isfile(SINCE_PATH):
            with open(SINCE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to load Twitter since map: {e}")
    return {}


def _save_since_map(since_map: dict) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = SINCE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(since_map, f, ensure_ascii=False, indent=2)
    os.replace(tmp, SINCE_PATH)


# ------------------ helpers ------------------

def _has_token(text: str, token: str) -> bool:
    token = token.strip()
    if not token:
        return False
    return re.search(rf"\b{re.escape(token)}\b", text, flags=re.IGNORECASE) is not None


def _matches_company_and_keyword(text: str) -> tuple[bool, dict]:
    """
    Enhanced Twitter matching logic with detailed match information
    """
    # Create a mock alert for consistency with main matching function
    mock_alert = {
        "title": "",
        "content": text,
        "text": text,  # Also set text field for better matching
        "url": "",
        "published": ""
    }

    # Import matching function to avoid circular dependency
    try:
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from src.main import matches_company_and_keyword
        return matches_company_and_keyword(mock_alert)
    except ImportError:
        # Fallback to simple matching if import fails
        match_details = {
            'matched_companies': [],
            'matched_keywords': [],
            'matched_tokens': [],
            'match_strategy': None,
            'confidence_score': 0,
            'match_reasons': [],
            'priority_level': None
        }
        
        text_lower = text.lower()
        
        # Check for company matches
        for c in COMPANIES:
            if isinstance(c, dict):
                company_name = c.get("name", "")
                aliases = c.get("aliases", [])
                all_names = [company_name] + aliases
                if any(name.lower() in text_lower for name in all_names if name):
                    match_details['matched_companies'].append(company_name)
        
        # Check for keywords
        for k in HIGH_CONFIDENCE_TGE_KEYWORDS:
            if k.lower() in text_lower:
                match_details['matched_keywords'].append(k)
        
        is_match = len(match_details['matched_companies']) > 0 and len(match_details['matched_keywords']) > 0
        if is_match:
            match_details['confidence_score'] = 60
            match_details['match_strategy'] = 'fallback'
            
        return is_match, match_details


def _call_with_backoff(fn, *args, **kwargs):
    delay = 1  # Start with shorter delay
    max_retries = 3  # Reduced retries
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except TooManyRequests:
            if attempt < max_retries - 1:
                time.sleep(min(delay, 30))  # Cap delay at 30 seconds
                delay = min(delay * 2, 30)
            else:
                raise
        except HTTPException as e:
            if attempt < max_retries - 1:
                time.sleep(min(delay, 15))  # Cap delay at 15 seconds
                delay = min(delay * 2, 15)
            else:
                raise
        except Exception as e:
            # For other exceptions, don't retry
            raise
    raise RuntimeError("Twitter API retries exhausted")


# ------------------ monitor class ------------------

class TwitterMonitor:
    """
    Twitter monitor that:
    - pulls user timelines incrementally using since_id
    - optionally runs combined (company AND keyword) searches
    - returns a list of alert dicts expected by main/email
    """

    def __init__(self):
        self.logger = logging.getLogger("twitter_monitor")
        
        # Initialize stats tracking
        self.total_processed = 0
        self.total_tge_tweets = 0
        self._recent_tweets = []  # Cache for recent tweets

        bearer = os.getenv("TWITTER_BEARER_TOKEN")
        if not bearer:
            self.logger.warning("TWITTER_BEARER_TOKEN missing; Twitter monitoring disabled")
            self.client = None
            self.api = None
            self._since = {}
            self.accounts: list[str] = []
            self.search_enabled = False
            return
        
        # Validate bearer token format
        if not self._validate_bearer_token(bearer):
            self.logger.error("Invalid TWITTER_BEARER_TOKEN format; Twitter monitoring disabled")
            self.client = None
            self.api = None
            self._since = {}
            self.accounts: list[str] = []
            self.search_enabled = False
            return

        self.client = tweepy.Client(bearer_token=bearer, wait_on_rate_limit=False)
        self.api = self.client  # maintain attribute used elsewhere

        # Accounts: use config-defined accounts or env comma list
        from config import TWITTER_ACCOUNTS
        env_users = os.getenv("TWITTER_USERS", "").strip()
        if env_users:
            self.accounts = [u.strip().lstrip("@") for u in env_users.split(",") if u.strip()]
        else:
            # Use accounts from config, removing @ symbols
            self.accounts = [acc.lstrip("@") for acc in TWITTER_ACCOUNTS if acc]

        # Toggle search if desired (default on)
        self.search_enabled = os.getenv("TWITTER_ENABLE_SEARCH", "1") not in {"0", "false", "False"}

        self._since = _load_since_map()

    # -------- public API expected by main.py --------

    def process_tweets(self) -> List[Dict]:
        if not self.client:
            self.logger.warning("Twitter client not available; skipping Twitter processing")
            return []

        out: list[dict] = []

        # 1) timelines
        if self.accounts:
            for handle in self.accounts[:5]:  # Limit to first 5 accounts to prevent hanging
                try:
                    u = _call_with_backoff(self.client.get_user, username=handle, user_fields=["id"])
                except Exception as e:
                    self.logger.warning(f"get_user({handle}) failed: {e}")
                    continue
                user = (u.data or None)
                if not user:
                    continue
                uid = str(user.id)
                try:
                    timeline_results = self._fetch_user_timeline(uid, handle)
                    out.extend(timeline_results)
                except Exception as e:
                    self.logger.warning(f"Failed to fetch timeline for {handle}: {e}")
                    continue
                time.sleep(0.2)  # Reduced sleep time

        # 2) combined queries (company AND keyword)
        if self.search_enabled:
            try:
                search_results = self._search_company_keyword_batches()
                out.extend(search_results)
            except Exception as e:
                self.logger.warning(f"Twitter search failed: {e}")
        
        # annotate as twitter and shape minimal fields downstream expects
        for a in out:
            a.setdefault("source", "Twitter")
            a.setdefault("source_type", "twitter")

        # Update stats
        self.total_processed += len(out)
        self.total_tge_tweets += len(out)
        
        # Cache recent tweets for daily summary
        self._recent_tweets.extend(out)
        # Keep only last 100 tweets to avoid memory issues
        self._recent_tweets = self._recent_tweets[-100:]

        # stats
        self.logger.info(f"process_tweets: produced {len(out)} candidate alerts")
        return out

    def _validate_bearer_token(self, token: str) -> bool:
        """Validate Twitter bearer token format."""
        if not token or not isinstance(token, str):
            return False
        
        # Remove "Bearer " prefix if present for validation
        clean_token = token.replace('Bearer ', '') if token.startswith('Bearer ') else token
        
        # Basic format validation - Twitter bearer tokens are typically 40+ characters
        if len(clean_token) < 40:
            return False
        
        # Check for common invalid patterns
        invalid_patterns = ['your_bearer_token', 'placeholder', 'test', 'example', 'test_bearer_token']
        if any(pattern in clean_token.lower() for pattern in invalid_patterns):
            return False
        
        return True

    def get_recent_tge_tweets(self, hours: int = 24) -> List[Dict]:
        """Return TGE tweets from the last N hours."""
        if not self._recent_tweets:
            return []
        
        from datetime import datetime, timezone, timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        recent = []
        for tweet in self._recent_tweets:
            try:
                # Parse published time
                published = tweet.get("published")
                if isinstance(published, str):
                    published = datetime.fromisoformat(published.replace('Z', '+00:00'))
                elif not isinstance(published, datetime):
                    continue
                    
                if published >= cutoff:
                    recent.append(tweet)
            except Exception as e:
                logging.getLogger(__name__).warning(f"Error processing tweet timestamp: {e}")
                continue
                
        return recent

    def get_stats(self) -> Dict:
        return {
            "total_processed": self.total_processed,
            "total_tge_tweets": self.total_tge_tweets
        }

    # -------- internals --------

    def _fetch_user_timeline(self, user_id: str, handle: str, max_results: int = 25) -> List[Dict]:
        alerts: list[dict] = []
        since_id = self._since.get(f"user:{user_id}")
        try:
            resp = _call_with_backoff(
                self.client.get_users_tweets,
                id=user_id,
                since_id=since_id,
                exclude=["retweets", "replies"],
                max_results=max_results,
                tweet_fields=["created_at", "text", "lang"]
            )
        except Exception as e:
            self.logger.warning(f"fetch timeline @{handle} failed: {e}")
            return alerts

        newest = since_id
        data = resp.data or []
        for t in data:
            try:
                # Validate tweet object
                if not hasattr(t, 'id') or not hasattr(t, 'text'):
                    continue
                    
                # Extract and validate text
                txt = getattr(t, 'text', '') or ""
                if not isinstance(txt, str):
                    txt = str(txt) if txt else ""
                txt = txt.strip()[:280]  # Limit to tweet length
                
                if not txt:
                    continue

                is_match, match_details = _matches_company_and_keyword(txt)
                if not is_match:
                    continue
                
                # Validate tweet ID
                tweet_id = str(getattr(t, 'id', ''))
                if not tweet_id or not tweet_id.isdigit():
                    continue
                
                # Validate handle
                if not handle or not isinstance(handle, str):
                    continue
                handle = handle.strip().lstrip('@')[:50]  # Limit handle length
                
                # Create URL safely
                url = f"https://x.com/{handle}/status/{tweet_id}"
                
                # Parse created_at safely
                published = None
                created_at = getattr(t, 'created_at', None)
                if created_at:
                    try:
                        if hasattr(created_at, 'isoformat'):
                            published = created_at.isoformat()
                        else:
                            published = str(created_at)
                    except Exception:
                        published = None
                
                alerts.append({
                    "title": f"@{handle}: possible TGE signal",
                    "text": txt,
                    "url": url,
                    "published": published,
                    "author": handle,
                    "tweet_id": tweet_id,
                    "channel": "twitter",
                    "match_details": match_details,
                })
                
                # Update newest ID safely
                try:
                    if newest is None or int(tweet_id) > int(newest or 0):
                        newest = tweet_id
                except (ValueError, TypeError):
                    pass
                    
            except Exception as e:
                self.logger.warning(f"Error processing tweet from @{handle}: {e}")
                continue

        if newest is not None:
            self._since[f"user:{user_id}"] = str(newest)
            _save_since_map(self._since)
        return alerts

    def _search_company_keyword_batches(self, per_query_limit: int = 25) -> List[Dict]:
        """
        Build queries like:
          ("offchain labs" OR "arbitrum") ("token" OR "tge" OR "airdrop") lang:en -is:retweet
        and page through a few until rate-limit is hit (backoff handles retries).
        Track a simple since_id per query key.
        """
        alerts: list[dict] = []

        # Build alias buckets for companies
        company_buckets: list[list[str]] = []
        for c in COMPANIES:
            if isinstance(c, dict):
                names = [c.get("name", "")] + (c.get("aliases", []) or [])
            else:
                names = [str(c)]
            names = [n.strip() for n in names if n and n.strip()]
            if names:
                company_buckets.append(names)

        if not company_buckets or not TGE_KEYWORDS:
            return alerts

        kw_clause = "(" + " OR ".join(f'"{k}"' if " " in k else k for k in TGE_KEYWORDS) + ")"
        for names in company_buckets:
            comp_clause = "(" + " OR ".join(f'"{n}"' if " " in n else n for n in names) + ")"
            q = f"{comp_clause} {kw_clause} lang:en -is:retweet"

            key = f"q:{comp_clause}|{kw_clause}"
            since_id = self._since.get(key)

            try:
                resp = _call_with_backoff(
                    self.client.search_recent_tweets,
                    query=q,
                    since_id=since_id,
                    max_results=min(100, per_query_limit),
                    tweet_fields=["created_at", "text", "lang"],
                )
            except TooManyRequests:
                self.logger.warning("Rate limited during search; continuing with backoff")
                continue
            except Exception as e:
                self.logger.warning(f"search_recent_tweets failed: {e}")
                continue

            newest = since_id
            for t in resp.data or []:
                txt = t.text or ""
                is_match, match_details = _matches_company_and_keyword(txt)
                if not is_match:
                    continue
                url = f"https://x.com/i/web/status/{t.id}"
                alerts.append({
                    "title": "Twitter search hit: possible TGE",
                    "text": txt,
                    "url": url,
                    "published": (t.created_at.isoformat() if getattr(t, "created_at", None) else None),
                    "tweet_id": str(t.id),
                    "channel": "twitter",
                    "match_details": match_details,
                })
                if newest is None or int(t.id) > int(newest or 0):
                    newest = str(t.id)

            if newest is not None:
                self._since[key] = str(newest)
                _save_since_map(self._since)
            time.sleep(0.6)  # spacing between query groups

        return alerts
