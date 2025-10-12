"""
Test Utilities and Helper Functions
Common utilities for test setup and assertions
"""

import os
import json
import time
from typing import Dict, List, Any
from unittest.mock import Mock
from datetime import datetime, timezone


class TestHelpers:
    """Helper methods for test setup and assertions"""

    @staticmethod
    def create_test_article(has_tge: bool = True, confidence: str = 'high') -> Dict:
        """
        Generate test article with specified characteristics

        Args:
            has_tge: Whether article is about a TGE
            confidence: Confidence level ('high', 'medium', 'low')

        Returns:
            Dictionary with article data
        """
        if has_tge:
            if confidence == 'high':
                return {
                    'title': 'Caldera TGE Announcement',
                    'url': 'https://example.com/caldera-tge',
                    'summary': 'Caldera announces Token Generation Event',
                    'content': 'Caldera Labs announces TGE with $CAL token distribution and airdrop',
                    'published': time.struct_time((2024, 1, 15, 12, 0, 0, 0, 0, 0)),
                    'source': 'https://example.com/feed.xml'
                }
            elif confidence == 'medium':
                return {
                    'title': 'Caldera Mainnet Launch',
                    'url': 'https://example.com/caldera-mainnet',
                    'summary': 'Caldera launches mainnet',
                    'content': 'Caldera Protocol launches mainnet with new features',
                    'published': time.struct_time((2024, 1, 15, 12, 0, 0, 0, 0, 0)),
                    'source': 'https://example.com/feed.xml'
                }
            else:  # low
                return {
                    'title': 'Caldera Update',
                    'url': 'https://example.com/caldera-update',
                    'summary': 'General update from Caldera',
                    'content': 'Caldera releases new documentation',
                    'published': time.struct_time((2024, 1, 15, 12, 0, 0, 0, 0, 0)),
                    'source': 'https://example.com/feed.xml'
                }
        else:
            return {
                'title': 'General Crypto News',
                'url': 'https://example.com/general-news',
                'summary': 'Market analysis',
                'content': 'Bitcoin and Ethereum prices analysis',
                'published': time.struct_time((2024, 1, 15, 12, 0, 0, 0, 0, 0)),
                'source': 'https://example.com/feed.xml'
            }

    @staticmethod
    def create_test_tweet(has_tge: bool = True, engagement: str = 'high') -> Dict:
        """
        Generate test tweet with specified characteristics

        Args:
            has_tge: Whether tweet is about a TGE
            engagement: Engagement level ('high', 'medium', 'low')

        Returns:
            Dictionary with tweet data
        """
        engagement_metrics = {
            'high': {'retweet_count': 500, 'like_count': 2000, 'impression_count': 100000},
            'medium': {'retweet_count': 50, 'like_count': 200, 'impression_count': 10000},
            'low': {'retweet_count': 5, 'like_count': 20, 'impression_count': 1000}
        }

        if has_tge:
            return {
                'id': '1234567890',
                'text': 'Caldera TGE is live! Claim your $CAL tokens now',
                'author_id': 'caldera_official',
                'created_at': datetime.now(timezone.utc),
                'metrics': engagement_metrics[engagement],
                'url': 'https://twitter.com/i/web/status/1234567890'
            }
        else:
            return {
                'id': '1234567891',
                'text': 'GM crypto! Another day of building',
                'author_id': 'crypto_user',
                'created_at': datetime.now(timezone.utc),
                'metrics': engagement_metrics[engagement],
                'url': 'https://twitter.com/i/web/status/1234567891'
            }

    @staticmethod
    def mock_rss_feed(company: str = "Caldera", keywords: List[str] = None) -> Mock:
        """
        Create mock RSS feed with specified content

        Args:
            company: Company name to include
            keywords: Keywords to include

        Returns:
            Mock feedparser response
        """
        keywords = keywords or ["TGE"]

        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed = Mock(title=f"{company} News Feed")
        mock_feed.entries = [
            Mock(
                link=f"https://example.com/{company.lower()}-article",
                title=f"{company} {keywords[0]} Announcement",
                summary=f"{company} announces {keywords[0]}",
                published_parsed=time.struct_time((2024, 1, 15, 12, 0, 0, 0, 0, 0))
            )
        ]

        return mock_feed

    @staticmethod
    def mock_article_content(company: str = "Caldera", has_tge: bool = True) -> Mock:
        """
        Create mock article content

        Args:
            company: Company name
            has_tge: Whether content includes TGE information

        Returns:
            Mock Article object
        """
        mock_article = Mock()

        if has_tge:
            mock_article.text = f"{company} announces Token Generation Event with ${company[:3].upper()} token"
        else:
            mock_article.text = f"{company} general update and news"

        return mock_article

    @staticmethod
    def assert_relevance_score(confidence: float, expected_range: tuple):
        """
        Assert confidence score is within expected range

        Args:
            confidence: Actual confidence score
            expected_range: Tuple of (min, max) expected values
        """
        min_conf, max_conf = expected_range
        assert min_conf <= confidence <= max_conf, \
            f"Confidence {confidence} not in range [{min_conf}, {max_conf}]"

    @staticmethod
    def assert_contains_keywords(text: str, keywords: List[str], min_matches: int = 1):
        """
        Assert text contains minimum number of keywords

        Args:
            text: Text to search
            keywords: Keywords to find
            min_matches: Minimum number of keywords to match
        """
        text_lower = text.lower()
        matches = sum(1 for keyword in keywords if keyword.lower() in text_lower)

        assert matches >= min_matches, \
            f"Found {matches} keywords, expected at least {min_matches}"

    @staticmethod
    def assert_performance(duration: float, max_duration: float, operation: str = "operation"):
        """
        Assert operation completed within time limit

        Args:
            duration: Actual duration in seconds
            max_duration: Maximum allowed duration
            operation: Name of operation for error message
        """
        assert duration <= max_duration, \
            f"{operation} took {duration:.2f}s, expected <= {max_duration:.2f}s"


class MockFilesystem:
    """Mock filesystem operations for testing"""

    def __init__(self):
        """Initialize mock filesystem"""
        self.files = {}

    def create_file(self, path: str, content: str):
        """Create a mock file"""
        self.files[path] = content

    def read_file(self, path: str) -> str:
        """Read a mock file"""
        return self.files.get(path, "")

    def file_exists(self, path: str) -> bool:
        """Check if mock file exists"""
        return path in self.files

    def delete_file(self, path: str):
        """Delete a mock file"""
        if path in self.files:
            del self.files[path]

    def list_files(self) -> List[str]:
        """List all mock files"""
        return list(self.files.keys())


class PerformanceTimer:
    """Timer for performance measurements"""

    def __init__(self):
        """Initialize timer"""
        self.start_time = None
        self.end_time = None
        self.measurements = []

    def start(self):
        """Start timing"""
        self.start_time = time.time()

    def stop(self) -> float:
        """
        Stop timing and return duration

        Returns:
            Duration in seconds
        """
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        self.measurements.append(duration)
        return duration

    def reset(self):
        """Reset timer"""
        self.start_time = None
        self.end_time = None

    def get_average(self) -> float:
        """
        Get average duration from all measurements

        Returns:
            Average duration in seconds
        """
        if not self.measurements:
            return 0.0
        return sum(self.measurements) / len(self.measurements)

    def get_stats(self) -> Dict[str, float]:
        """
        Get statistics from all measurements

        Returns:
            Dictionary with min, max, avg, total
        """
        if not self.measurements:
            return {'min': 0, 'max': 0, 'avg': 0, 'total': 0, 'count': 0}

        return {
            'min': min(self.measurements),
            'max': max(self.measurements),
            'avg': self.get_average(),
            'total': sum(self.measurements),
            'count': len(self.measurements)
        }


def create_test_cache() -> Dict:
    """Create test cache structure"""
    return {
        'articles': {},
        'summaries': {}
    }


def create_test_state() -> Dict:
    """Create test state structure"""
    return {
        'seen_urls': {},
        'feed_stats': {},
        'last_full_scan': None,
        'failed_feeds': {},
        'article_fetch_stats': {}
    }


def validate_article_structure(article: Dict) -> bool:
    """
    Validate article has required fields

    Args:
        article: Article dictionary to validate

    Returns:
        True if valid, False otherwise
    """
    required_fields = ['title', 'url', 'summary', 'published', 'source']
    return all(field in article for field in required_fields)


def validate_tweet_structure(tweet: Dict) -> bool:
    """
    Validate tweet has required fields

    Args:
        tweet: Tweet dictionary to validate

    Returns:
        True if valid, False otherwise
    """
    required_fields = ['id', 'text', 'author_id', 'created_at']
    return all(field in tweet for field in required_fields)
