"""
Utility functions and classes for the Crypto TGE Monitor

This module provides common utilities including error handling, retry logic,
validation, and other shared functionality.
"""

import time
import logging
import functools
import hashlib
import json
import os
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class RetryConfig:
    """Configuration for retry logic."""
    
    def __init__(
        self,
        total: int = 3,
        backoff_factor: float = 1.0,
        status_forcelist: tuple = (500, 502, 504),
        allowed_methods: tuple = ("HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE")
    ):
        self.total = total
        self.backoff_factor = backoff_factor
        self.status_forcelist = status_forcelist
        self.allowed_methods = allowed_methods


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator to retry a function on failure with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry on
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        logging.getLogger(__name__).error(
                            f"Function {func.__name__} failed after {max_retries} retries: {str(e)}"
                        )
                        raise e
                    
                    logging.getLogger(__name__).warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)}. "
                        f"Retrying in {current_delay:.2f} seconds..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
            
            raise last_exception
        return wrapper
    return decorator


def create_robust_session(retry_config: Optional[RetryConfig] = None) -> requests.Session:
    """
    Create a requests session with robust retry logic and proper headers.
    
    Args:
        retry_config: Configuration for retry logic
        
    Returns:
        Configured requests session
    """
    if retry_config is None:
        retry_config = RetryConfig()
    
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=retry_config.total,
        backoff_factor=retry_config.backoff_factor,
        status_forcelist=retry_config.status_forcelist,
        allowed_methods=retry_config.allowed_methods
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Set default headers
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    
    return session


def generate_content_hash(content: str) -> str:
    """
    Generate a hash for content to detect duplicates.
    
    Args:
        content: Content to hash
        
    Returns:
        SHA-256 hash of the content
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def is_content_duplicate(content: str, seen_hashes: set) -> bool:
    """
    Check if content is a duplicate based on hash.
    
    Args:
        content: Content to check
        seen_hashes: Set of previously seen hashes
        
    Returns:
        True if content is duplicate, False otherwise
    """
    content_hash = generate_content_hash(content)
    if content_hash in seen_hashes:
        return True
    
    seen_hashes.add(content_hash)
    return False


def validate_url(url: str) -> bool:
    """
    Validate if a URL is properly formatted.
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL is valid, False otherwise
    """
    try:
        from urllib.parse import urlparse
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception as e:
        logging.getLogger(__name__).warning(f"URL validation failed: {e}")
        return False


def validate_email(email: str) -> bool:
    """
    Validate if an email address is properly formatted.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email is valid, False otherwise
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def sanitize_text(text: str, max_length: int = 1000, escape_html: bool = True) -> str:
    """
    Enhanced sanitize text with comprehensive security protections.
    
    Args:
        text: Text to sanitize
        max_length: Maximum length of the text
        escape_html: Whether to escape HTML entities for security
        
    Returns:
        Sanitized text
    """
    if not text or not isinstance(text, str):
        return ""
    
    import re
    import html
    
    # Remove null bytes and other dangerous characters
    text = text.replace('\x00', '')
    
    # Remove control characters (except tabs, newlines, carriage returns)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    
    # Remove potentially dangerous Unicode characters
    # Remove zero-width characters that could be used for obfuscation
    text = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]', '', text)
    
    # Remove script injection patterns (basic protection)
    dangerous_patterns = [
        r'<\s*script[^>]*>.*?<\s*/\s*script\s*>',
        r'javascript\s*:',
        r'vbscript\s*:',
        r'data\s*:',
        r'on\w+\s*=',  # onclick, onload, etc.
    ]
    
    for pattern in dangerous_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Escape HTML entities for security if requested
    if escape_html:
        text = html.escape(text, quote=True)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Limit length with intelligent truncation
    if len(text) > max_length:
        # Try to truncate at word boundary
        if max_length > 10:
            truncated = text[:max_length-3].rsplit(' ', 1)[0]
            if len(truncated) >= max_length * 0.8:  # If we got at least 80% of desired length
                text = truncated + "..."
            else:
                text = text[:max_length-3] + "..."
        else:
            text = text[:max_length-3] + "..."
    
    return text


def sanitize_html_content(content: str) -> str:
    """
    Sanitize HTML content for safe email inclusion.
    
    Args:
        content: HTML content to sanitize
        
    Returns:
        Sanitized HTML content
    """
    if not content or not isinstance(content, str):
        return ""
    
    import re
    import html
    
    # Remove dangerous HTML elements entirely
    dangerous_tags = [
        'script', 'iframe', 'object', 'embed', 'form', 'input', 
        'textarea', 'button', 'select', 'option', 'meta', 'link',
        'style', 'base', 'applet', 'svg'
    ]
    
    for tag in dangerous_tags:
        # Remove both opening and closing tags
        content = re.sub(f'<\s*{tag}[^>]*>.*?<\s*/\s*{tag}\s*>', '', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(f'<\s*{tag}[^>]*/?>', '', content, flags=re.IGNORECASE)
    
    # Remove dangerous attributes from remaining tags
    dangerous_attrs = [
        'onclick', 'onload', 'onmouseover', 'onerror', 'onsubmit',
        'onchange', 'onfocus', 'onblur', 'onkeydown', 'onkeyup',
        'style', 'javascript:', 'vbscript:', 'data:'
    ]
    
    for attr in dangerous_attrs:
        content = re.sub(f'{attr}\s*=\s*["\'][^"\']*["\']', '', content, flags=re.IGNORECASE)
        content = re.sub(f'{attr}\s*=\s*[^>\s]*', '', content, flags=re.IGNORECASE)
    
    # Limit content size to prevent DoS
    if len(content) > 1024 * 1024:  # 1MB limit
        content = content[:1024 * 1024]
    
    return content


def validate_and_sanitize_url(url: str) -> str:
    """
    Validate and sanitize URLs for safe inclusion in emails.
    
    Args:
        url: URL to validate and sanitize
        
    Returns:
        Sanitized URL or empty string if invalid
    """
    if not url or not isinstance(url, str):
        return ""
    
    import re
    from urllib.parse import urlparse, urlunparse
    
    # Remove potentially dangerous characters
    url = url.strip().replace('\x00', '').replace('\n', '').replace('\r', '')
    
    # Check for dangerous schemes
    dangerous_schemes = ['javascript', 'vbscript', 'data', 'file']
    
    try:
        parsed = urlparse(url)
        
        # Reject dangerous schemes
        if parsed.scheme.lower() in dangerous_schemes:
            return ""
        
        # Only allow http and https for external links
        if parsed.scheme and parsed.scheme.lower() not in ['http', 'https']:
            return ""
        
        # Basic validation
        if not parsed.netloc and parsed.scheme:  # Has scheme but no domain
            return ""
        
        # Reconstruct URL to normalize it
        clean_url = urlunparse(parsed)
        
        # Additional length check
        if len(clean_url) > 2048:  # Standard URL length limit
            return ""
        
        return clean_url
        
    except Exception:
        return ""


def format_timestamp(timestamp: Optional[datetime] = None, format_str: str = "%Y-%m-%d %H:%M:%S UTC") -> str:
    """
    Format a timestamp for display.
    
    Args:
        timestamp: Timestamp to format (defaults to now)
        format_str: Format string for the timestamp
        
    Returns:
        Formatted timestamp string
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    return timestamp.strftime(format_str)


def parse_date_flexible(date_str: str) -> Optional[datetime]:
    """
    Parse a date string using multiple common formats.
    
    Args:
        date_str: Date string to parse
        
    Returns:
        Parsed datetime object or None if parsing fails
    """
    if not date_str:
        return None
    
    # Common date formats
    formats = [
        '%a, %d %b %Y %H:%M:%S %z',
        '%a, %d %b %Y %H:%M:%S %Z',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%d %H:%M:%S',
        '%a, %d %b %Y %H:%M:%S',
        '%Y-%m-%d',
        '%d/%m/%Y',
        '%m/%d/%Y',
        '%d-%m-%Y',
        '%m-%d-%Y'
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # Try email.utils as fallback
    try:
        import email.utils
        parsed_date = email.utils.parsedate_tz(date_str)
        if parsed_date:
            return datetime(*parsed_date[:6])
    except Exception as e:
        logging.getLogger(__name__).warning(f"Email utils parsing failed: {e}")
    
    return None


def load_json_file(file_path: str, default: Any = None) -> Any:
    """
    Load JSON data from a file with error handling.
    
    Args:
        file_path: Path to the JSON file
        default: Default value to return if file doesn't exist or is invalid
        
    Returns:
        Loaded JSON data or default value
    """
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logging.getLogger(__name__).warning(f"Failed to load JSON file {file_path}: {str(e)}")
    
    return default


def save_json_file(file_path: str, data: Any, create_dirs: bool = True) -> bool:
    """
    Save data to a JSON file with error handling.
    
    Args:
        file_path: Path to save the JSON file
        data: Data to save
        create_dirs: Whether to create parent directories if they don't exist
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if create_dirs:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        return True
    except (IOError, TypeError) as e:
        logging.getLogger(__name__).error(f"Failed to save JSON file {file_path}: {str(e)}")
        return False


def setup_structured_logging(
    log_file: str,
    log_level: str = "INFO",
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Setup structured logging with file rotation.
    
    Args:
        log_file: Path to the log file
        log_level: Logging level
        max_file_size: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        
    Returns:
        Configured logger
    """
    import logging.handlers
    
    # Ensure log directory exists
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


def calculate_relevance_score(
    companies: List[str],
    keywords: List[str],
    text: str,
    keyword_weights: Optional[Dict[str, float]] = None,
    company_weight: float = 0.3,
    sentiment_weight: float = 0.1,
    urgency_weight: float = 0.05
) -> float:
    """
    Calculate relevance score for TGE detection.
    
    Args:
        companies: List of mentioned companies
        keywords: List of found keywords
        text: Full text content
        keyword_weights: Custom weights for keywords
        company_weight: Weight for company mentions
        sentiment_weight: Weight for sentiment analysis
        urgency_weight: Weight for urgency indicators
        
    Returns:
        Relevance score between 0.0 and 1.0
    """
    score = 0.0
    
    # Company mention weight
    score += len(companies) * company_weight
    
    # Default keyword weights
    if keyword_weights is None:
        keyword_weights = {
            'tge': 0.4,
            'token generation event': 0.4,
            'token launch': 0.3,
            'airdrop': 0.25,
            'token sale': 0.2,
            'ico': 0.2,
            'ido': 0.2,
            'token listing': 0.15,
            'token distribution': 0.15
        }
    
    # Keyword weight
    for keyword in keywords:
        weight = keyword_weights.get(keyword.lower(), 0.1)
        score += weight
    
    # Sentiment analysis
    try:
        from textblob import TextBlob
        blob = TextBlob(text)
        sentiment = blob.sentiment.polarity
        
        if sentiment > 0.1:
            score += sentiment_weight
    except Exception as e:
        logging.getLogger(__name__).warning(f"Sentiment analysis failed: {e}")
    
    # Urgency indicators
    urgency_words = ['announce', 'launch', 'release', 'coming', 'soon', 'date', 'schedule', 'tomorrow', 'today']
    urgency_count = sum(1 for word in urgency_words if word in text.lower())
    score += urgency_count * urgency_weight
    
    return min(score, 1.0)  # Cap at 1.0


def is_recent_content(timestamp: Optional[datetime], hours: int = 24) -> bool:
    """
    Check if content is recent enough to process.
    
    Args:
        timestamp: Timestamp to check
        hours: Number of hours to consider as recent
        
    Returns:
        True if content is recent, False otherwise
    """
    if timestamp is None:
        return False
    
    cutoff_time = datetime.now() - timedelta(hours=hours)
    return timestamp > cutoff_time


def extract_domain(url: str) -> str:
    """
    Extract domain name from URL.
    
    Args:
        url: URL to extract domain from
        
    Returns:
        Domain name
    """
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        return domain.replace('www.', '').split('.')[0].title()
    except Exception as e:
        logging.getLogger(__name__).warning(f"Domain extraction failed: {e}")
        return "Unknown"


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """
    Truncate text to specified length with suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncating
        
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


class HealthChecker:
    """Health check utility for monitoring system components."""
    
    def __init__(self):
        self.checks = {}
    
    def register_check(self, name: str, check_func: Callable[[], bool], description: str = ""):
        """Register a health check function."""
        self.checks[name] = {
            'function': check_func,
            'description': description,
            'last_check': None,
            'last_result': None
        }
    
    def run_checks(self) -> Dict[str, Dict[str, Any]]:
        """Run all registered health checks."""
        results = {}
        
        for name, check_info in self.checks.items():
            try:
                start_time = time.time()
                result = check_info['function']()
                duration = time.time() - start_time
                
                check_info['last_check'] = datetime.now()
                check_info['last_result'] = result
                
                results[name] = {
                    'status': 'healthy' if result else 'unhealthy',
                    'result': result,
                    'duration': duration,
                    'description': check_info['description'],
                    'last_check': check_info['last_check'].isoformat()
                }
            except Exception as e:
                check_info['last_check'] = datetime.now()
                check_info['last_result'] = False
                
                results[name] = {
                    'status': 'error',
                    'result': False,
                    'error': str(e),
                    'description': check_info['description'],
                    'last_check': check_info['last_check'].isoformat()
                }
        
        return results
    
    def get_overall_status(self) -> str:
        """Get overall system health status."""
        results = self.run_checks()
        
        if not results:
            return 'unknown'
        
        statuses = [result['status'] for result in results.values()]
        
        if all(status == 'healthy' for status in statuses):
            return 'healthy'
        elif any(status == 'error' for status in statuses):
            return 'error'
        else:
            return 'degraded'
