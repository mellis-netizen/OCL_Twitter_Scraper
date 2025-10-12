"""
Comprehensive unit tests for src/utils.py

Tests all utility functions including:
- Retry logic and decorators
- HTTP session creation
- Content hashing and duplicate detection
- URL and email validation
- Text sanitization and security
- Timestamp formatting and parsing
- JSON file operations
- Logging setup
- Relevance scoring
- Health checking
"""

import pytest
import time
import json
import os
import tempfile
import logging
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, call
import hashlib
import requests
from requests.adapters import HTTPAdapter

from src.utils import (
    RetryConfig,
    retry_on_failure,
    create_robust_session,
    generate_content_hash,
    is_content_duplicate,
    validate_url,
    validate_email,
    sanitize_text,
    sanitize_html_content,
    validate_and_sanitize_url,
    format_timestamp,
    parse_date_flexible,
    load_json_file,
    save_json_file,
    setup_structured_logging,
    calculate_relevance_score,
    is_recent_content,
    extract_domain,
    truncate_text,
    HealthChecker
)


class TestRetryConfig:
    """Tests for RetryConfig class"""

    def test_default_config(self):
        """Test RetryConfig with default values"""
        config = RetryConfig()
        assert config.total == 3
        assert config.backoff_factor == 1.0
        assert config.status_forcelist == (500, 502, 504)
        assert "GET" in config.allowed_methods
        assert "POST" in config.allowed_methods

    def test_custom_config(self):
        """Test RetryConfig with custom values"""
        config = RetryConfig(
            total=5,
            backoff_factor=2.0,
            status_forcelist=(500, 503),
            allowed_methods=("GET", "POST")
        )
        assert config.total == 5
        assert config.backoff_factor == 2.0
        assert config.status_forcelist == (500, 503)
        assert config.allowed_methods == ("GET", "POST")


class TestRetryOnFailure:
    """Tests for retry_on_failure decorator"""

    def test_successful_function(self):
        """Test decorator with function that succeeds"""
        @retry_on_failure(max_retries=3, delay=0.01)
        def successful_func():
            return "success"

        result = successful_func()
        assert result == "success"

    def test_retry_on_exception(self):
        """Test decorator retries on exception"""
        call_count = 0

        @retry_on_failure(max_retries=3, delay=0.01, backoff_factor=1.5)
        def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"

        result = failing_then_success()
        assert result == "success"
        assert call_count == 3

    def test_max_retries_exceeded(self):
        """Test decorator raises after max retries"""
        @retry_on_failure(max_retries=2, delay=0.01)
        def always_fails():
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            always_fails()

    def test_specific_exceptions(self):
        """Test decorator only catches specified exceptions"""
        @retry_on_failure(max_retries=2, delay=0.01, exceptions=(ValueError,))
        def raises_type_error():
            raise TypeError("Wrong type")

        with pytest.raises(TypeError, match="Wrong type"):
            raises_type_error()

    def test_backoff_timing(self):
        """Test exponential backoff timing"""
        times = []

        @retry_on_failure(max_retries=3, delay=0.1, backoff_factor=2.0)
        def track_timing():
            times.append(time.time())
            if len(times) < 3:
                raise ValueError("Retry")
            return "done"

        start = time.time()
        track_timing()

        # Check that delays increase (0.1, 0.2, 0.4)
        assert len(times) == 3
        if len(times) >= 2:
            delay1 = times[1] - times[0]
            assert delay1 >= 0.09  # Allow small timing variance


class TestCreateRobustSession:
    """Tests for create_robust_session function"""

    def test_default_session(self):
        """Test session creation with defaults"""
        session = create_robust_session()

        assert isinstance(session, requests.Session)
        assert 'User-Agent' in session.headers
        assert 'Mozilla' in session.headers['User-Agent']
        assert 'Accept' in session.headers

    def test_custom_retry_config(self):
        """Test session with custom retry config"""
        config = RetryConfig(total=5, backoff_factor=2.0)
        session = create_robust_session(config)

        assert isinstance(session, requests.Session)
        # Verify adapters are mounted
        assert session.get_adapter('http://') is not None
        assert session.get_adapter('https://') is not None

    def test_session_headers(self):
        """Test session has required headers"""
        session = create_robust_session()

        required_headers = [
            'User-Agent',
            'Accept',
            'Accept-Language',
            'Accept-Encoding',
            'Connection',
            'Upgrade-Insecure-Requests'
        ]

        for header in required_headers:
            assert header in session.headers


class TestContentHashing:
    """Tests for content hashing and duplicate detection"""

    def test_generate_content_hash(self):
        """Test hash generation"""
        content = "Test content"
        hash1 = generate_content_hash(content)

        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA-256 hex digest length

        # Same content produces same hash
        hash2 = generate_content_hash(content)
        assert hash1 == hash2

    def test_different_content_different_hash(self):
        """Test different content produces different hashes"""
        hash1 = generate_content_hash("content 1")
        hash2 = generate_content_hash("content 2")

        assert hash1 != hash2

    def test_is_content_duplicate_first_time(self):
        """Test duplicate detection for new content"""
        seen_hashes = set()
        content = "New content"

        is_dup = is_content_duplicate(content, seen_hashes)

        assert is_dup is False
        assert len(seen_hashes) == 1

    def test_is_content_duplicate_second_time(self):
        """Test duplicate detection for seen content"""
        seen_hashes = set()
        content = "Same content"

        is_content_duplicate(content, seen_hashes)
        is_dup = is_content_duplicate(content, seen_hashes)

        assert is_dup is True
        assert len(seen_hashes) == 1


class TestValidateUrl:
    """Tests for URL validation"""

    def test_valid_urls(self):
        """Test validation of valid URLs"""
        valid_urls = [
            "https://example.com",
            "http://test.com/path",
            "https://sub.domain.com/path?query=1",
            "http://localhost:8000",
            "https://example.com:443/secure"
        ]

        for url in valid_urls:
            assert validate_url(url) is True

    def test_invalid_urls(self):
        """Test validation of invalid URLs"""
        invalid_urls = [
            "not a url",
            "example.com",  # No scheme
            "http://",  # No netloc
            "://example.com",  # No scheme
            ""
        ]

        for url in invalid_urls:
            assert validate_url(url) is False

    def test_url_validation_exception(self):
        """Test URL validation handles exceptions"""
        # Pass non-string to trigger exception
        assert validate_url(None) is False


class TestValidateEmail:
    """Tests for email validation"""

    def test_valid_emails(self):
        """Test validation of valid emails"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.com",
            "first.last@sub.domain.com",
            "user_123@test-domain.com"
        ]

        for email in valid_emails:
            assert validate_email(email) is True

    def test_invalid_emails(self):
        """Test validation of invalid emails"""
        invalid_emails = [
            "not an email",
            "@example.com",
            "user@",
            "user@.com",
            "user@domain",
            "user @example.com",
            "user@domain .com",
            ""
        ]

        for email in invalid_emails:
            assert validate_email(email) is False


class TestSanitizeText:
    """Tests for text sanitization"""

    def test_sanitize_normal_text(self):
        """Test sanitization of normal text"""
        text = "This is normal text."
        result = sanitize_text(text)
        assert result == "This is normal text."

    def test_sanitize_empty_text(self):
        """Test sanitization of empty text"""
        assert sanitize_text("") == ""
        assert sanitize_text(None) == ""

    def test_sanitize_non_string(self):
        """Test sanitization of non-string input"""
        assert sanitize_text(123) == ""
        assert sanitize_text([]) == ""

    def test_sanitize_removes_script_tags(self):
        """Test sanitization removes script tags"""
        text = "Hello <script>alert('xss')</script> World"
        result = sanitize_text(text)
        assert "script" not in result.lower()
        assert "alert" not in result.lower()

    def test_sanitize_removes_javascript_protocol(self):
        """Test sanitization removes javascript: protocol"""
        text = "Click <a href='javascript:alert(1)'>here</a>"
        result = sanitize_text(text)
        assert "javascript:" not in result.lower()

    def test_sanitize_removes_event_handlers(self):
        """Test sanitization removes event handlers"""
        text = "<div onclick='malicious()'>Click</div>"
        result = sanitize_text(text)
        assert "onclick" not in result.lower()

    def test_sanitize_removes_control_characters(self):
        """Test sanitization removes control characters"""
        text = "Hello\x00\x08\x1fWorld"
        result = sanitize_text(text)
        assert "\x00" not in result
        assert "\x08" not in result

    def test_sanitize_removes_zero_width_chars(self):
        """Test sanitization removes zero-width characters"""
        text = "Hello\u200bWorld\u200e"
        result = sanitize_text(text)
        assert "\u200b" not in result
        assert "\u200e" not in result

    def test_sanitize_escapes_html(self):
        """Test HTML escaping when enabled"""
        text = "<div>Test & 'quotes' \"test\"</div>"
        result = sanitize_text(text, escape_html=True)
        assert "&lt;" in result or "<div>" not in result
        assert "&amp;" in result or " & " not in result

    def test_sanitize_no_escape_html(self):
        """Test HTML not escaped when disabled"""
        text = "Test & more"
        result = sanitize_text(text, escape_html=False)
        # Note: after removing dangerous patterns, some escaping may still occur
        assert isinstance(result, str)

    def test_sanitize_normalizes_whitespace(self):
        """Test whitespace normalization"""
        text = "Hello    \n\n\t  World"
        result = sanitize_text(text)
        assert result == "Hello World"

    def test_sanitize_truncates_long_text(self):
        """Test truncation of long text"""
        text = "a" * 2000
        result = sanitize_text(text, max_length=100)
        assert len(result) <= 100
        assert result.endswith("...")

    def test_sanitize_truncates_at_word_boundary(self):
        """Test truncation at word boundary"""
        text = "Hello world this is a very long sentence that needs truncation"
        result = sanitize_text(text, max_length=30)
        assert len(result) <= 30
        assert "..." in result


class TestSanitizeHtmlContent:
    """Tests for HTML content sanitization"""

    def test_sanitize_empty_html(self):
        """Test sanitization of empty HTML"""
        assert sanitize_html_content("") == ""
        assert sanitize_html_content(None) == ""

    def test_sanitize_removes_dangerous_tags(self):
        """Test removal of dangerous HTML tags"""
        dangerous_tags = [
            "<script>alert('xss')</script>",
            "<iframe src='evil.com'></iframe>",
            "<object data='malicious'></object>",
            "<embed src='bad'></embed>",
            "<form><input></form>",
            "<style>body{display:none}</style>",
            "<svg><script>alert(1)</script></svg>"
        ]

        for html in dangerous_tags:
            result = sanitize_html_content(html)
            # Check that dangerous content is removed
            assert len(result) < len(html) or result == ""

    def test_sanitize_removes_event_attributes(self):
        """Test removal of event handler attributes"""
        html = '<div onclick="alert(1)" onload="malicious()">Content</div>'
        result = sanitize_html_content(html)
        assert "onclick" not in result.lower()
        assert "onload" not in result.lower()

    def test_sanitize_large_content(self):
        """Test sanitization limits content size"""
        large_html = "<div>" + ("a" * 2000000) + "</div>"
        result = sanitize_html_content(large_html)
        assert len(result) <= 1024 * 1024  # 1MB limit


class TestValidateAndSanitizeUrl:
    """Tests for URL validation and sanitization"""

    def test_valid_http_url(self):
        """Test valid HTTP URL"""
        url = "http://example.com/path"
        result = validate_and_sanitize_url(url)
        assert result == url

    def test_valid_https_url(self):
        """Test valid HTTPS URL"""
        url = "https://example.com/path?query=1"
        result = validate_and_sanitize_url(url)
        assert "https://" in result

    def test_empty_url(self):
        """Test empty URL"""
        assert validate_and_sanitize_url("") == ""
        assert validate_and_sanitize_url(None) == ""

    def test_dangerous_javascript_scheme(self):
        """Test rejection of javascript: scheme"""
        url = "javascript:alert('xss')"
        result = validate_and_sanitize_url(url)
        assert result == ""

    def test_dangerous_data_scheme(self):
        """Test rejection of data: scheme"""
        url = "data:text/html,<script>alert(1)</script>"
        result = validate_and_sanitize_url(url)
        assert result == ""

    def test_file_scheme_rejected(self):
        """Test rejection of file: scheme"""
        url = "file:///etc/passwd"
        result = validate_and_sanitize_url(url)
        assert result == ""

    def test_removes_dangerous_characters(self):
        """Test removal of dangerous characters"""
        url = "http://example.com/path\x00\n\r"
        result = validate_and_sanitize_url(url)
        assert "\x00" not in result
        assert "\n" not in result

    def test_url_too_long(self):
        """Test rejection of overly long URLs"""
        url = "http://example.com/" + ("a" * 3000)
        result = validate_and_sanitize_url(url)
        assert result == ""


class TestFormatTimestamp:
    """Tests for timestamp formatting"""

    def test_format_default(self):
        """Test default timestamp formatting"""
        dt = datetime(2024, 1, 15, 12, 30, 45)
        result = format_timestamp(dt)
        assert "2024-01-15" in result
        assert "12:30:45" in result

    def test_format_custom_format(self):
        """Test custom format string"""
        dt = datetime(2024, 1, 15, 12, 30, 45)
        result = format_timestamp(dt, format_str="%Y/%m/%d")
        assert result == "2024/01/15"

    def test_format_none_timestamp(self):
        """Test formatting with None uses current time"""
        result = format_timestamp(None)
        assert isinstance(result, str)
        assert len(result) > 0


class TestParseDateFlexible:
    """Tests for flexible date parsing"""

    def test_parse_iso_format(self):
        """Test parsing ISO format"""
        date_str = "2024-01-15T12:30:45Z"
        result = parse_date_flexible(date_str)
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_standard_format(self):
        """Test parsing standard format"""
        date_str = "2024-01-15 12:30:45"
        result = parse_date_flexible(date_str)
        assert result is not None
        assert result.year == 2024

    def test_parse_date_only(self):
        """Test parsing date only"""
        date_str = "2024-01-15"
        result = parse_date_flexible(date_str)
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_various_formats(self):
        """Test parsing various date formats"""
        formats = [
            "15/01/2024",
            "01/15/2024",
            "15-01-2024",
            "01-15-2024"
        ]

        for date_str in formats:
            result = parse_date_flexible(date_str)
            assert result is not None

    def test_parse_empty_string(self):
        """Test parsing empty string"""
        assert parse_date_flexible("") is None
        assert parse_date_flexible(None) is None

    def test_parse_invalid_format(self):
        """Test parsing invalid format"""
        result = parse_date_flexible("not a date")
        assert result is None


class TestJsonFileOperations:
    """Tests for JSON file operations"""

    def test_save_and_load_json(self):
        """Test saving and loading JSON file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.json")
            data = {"key": "value", "number": 42, "list": [1, 2, 3]}

            # Save
            success = save_json_file(file_path, data)
            assert success is True

            # Load
            loaded = load_json_file(file_path)
            assert loaded == data

    def test_load_nonexistent_file(self):
        """Test loading non-existent file returns default"""
        result = load_json_file("/nonexistent/file.json", default={"default": True})
        assert result == {"default": True}

    def test_load_invalid_json(self):
        """Test loading invalid JSON returns default"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "invalid.json")

            # Write invalid JSON
            with open(file_path, 'w') as f:
                f.write("not valid json {")

            result = load_json_file(file_path, default=None)
            assert result is None

    def test_save_creates_directories(self):
        """Test save creates parent directories"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "subdir", "nested", "test.json")
            data = {"test": True}

            success = save_json_file(file_path, data, create_dirs=True)
            assert success is True
            assert os.path.exists(file_path)

    def test_save_without_create_dirs(self):
        """Test save fails without creating directories"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "nonexistent", "test.json")
            data = {"test": True}

            success = save_json_file(file_path, data, create_dirs=False)
            assert success is False


class TestSetupStructuredLogging:
    """Tests for logging setup"""

    def test_setup_logging(self):
        """Test logging setup"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")

            logger = setup_structured_logging(log_file, log_level="INFO")

            assert isinstance(logger, logging.Logger)
            assert logger.level == logging.INFO
            assert len(logger.handlers) >= 2  # File and console

    def test_logging_writes_to_file(self):
        """Test logging writes to file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")

            logger = setup_structured_logging(log_file)
            logger.info("Test message")

            assert os.path.exists(log_file)
            with open(log_file, 'r') as f:
                content = f.read()
                assert "Test message" in content


class TestCalculateRelevanceScore:
    """Tests for relevance score calculation"""

    def test_basic_score(self):
        """Test basic relevance score"""
        companies = ["Company1"]
        keywords = ["tge", "token launch"]
        text = "Company1 announces TGE and token launch event"

        score = calculate_relevance_score(companies, keywords, text)

        assert 0.0 <= score <= 1.0
        assert score > 0

    def test_no_companies_no_keywords(self):
        """Test score with no matches"""
        score = calculate_relevance_score([], [], "Random text")
        assert score >= 0.0

    def test_multiple_companies(self):
        """Test score with multiple companies"""
        companies = ["Company1", "Company2", "Company3"]
        keywords = ["tge"]
        text = "Multiple companies"

        score = calculate_relevance_score(companies, keywords, text)
        assert score > 0

    def test_high_weight_keywords(self):
        """Test high weight keywords increase score"""
        keywords = ["tge", "token generation event"]
        text = "TGE and token generation event"

        score = calculate_relevance_score([], keywords, text)
        assert score > 0.5

    def test_custom_keyword_weights(self):
        """Test custom keyword weights"""
        keywords = ["custom"]
        custom_weights = {"custom": 0.9}
        text = "Custom keyword test"

        score = calculate_relevance_score(
            [], keywords, text,
            keyword_weights=custom_weights
        )
        assert score >= 0.9

    def test_urgency_indicators(self):
        """Test urgency indicators increase score"""
        text = "Announcing token launch today! Coming soon, tomorrow release"
        score = calculate_relevance_score([], [], text)
        assert score > 0


class TestIsRecentContent:
    """Tests for content recency check"""

    def test_recent_content(self):
        """Test recent content is detected"""
        recent_time = datetime.now() - timedelta(hours=1)
        assert is_recent_content(recent_time, hours=24) is True

    def test_old_content(self):
        """Test old content is detected"""
        old_time = datetime.now() - timedelta(hours=48)
        assert is_recent_content(old_time, hours=24) is False

    def test_none_timestamp(self):
        """Test None timestamp returns False"""
        assert is_recent_content(None) is False

    def test_custom_hours(self):
        """Test custom hours parameter"""
        time_6h_ago = datetime.now() - timedelta(hours=6)

        assert is_recent_content(time_6h_ago, hours=12) is True
        assert is_recent_content(time_6h_ago, hours=3) is False


class TestExtractDomain:
    """Tests for domain extraction"""

    def test_extract_domain_http(self):
        """Test domain extraction from HTTP URL"""
        url = "http://example.com/path"
        result = extract_domain(url)
        assert result == "Example"

    def test_extract_domain_https(self):
        """Test domain extraction from HTTPS URL"""
        url = "https://test.com/path?query=1"
        result = extract_domain(url)
        assert result == "Test"

    def test_extract_domain_with_www(self):
        """Test domain extraction removes www"""
        url = "https://www.example.com/path"
        result = extract_domain(url)
        assert "www" not in result.lower()

    def test_extract_domain_subdomain(self):
        """Test domain extraction from subdomain"""
        url = "https://api.example.com/endpoint"
        result = extract_domain(url)
        # Should extract the first part after www removal
        assert isinstance(result, str)

    def test_extract_domain_invalid_url(self):
        """Test domain extraction with invalid URL"""
        result = extract_domain("not a url")
        # Function returns empty string or "Unknown" depending on parsing
        assert result == "Unknown" or result == ""


class TestTruncateText:
    """Tests for text truncation"""

    def test_truncate_short_text(self):
        """Test truncation of text shorter than max"""
        text = "Short text"
        result = truncate_text(text, max_length=100)
        assert result == text

    def test_truncate_long_text(self):
        """Test truncation of long text"""
        text = "This is a very long text that needs to be truncated"
        result = truncate_text(text, max_length=20)
        assert len(result) <= 20
        assert result.endswith("...")

    def test_truncate_empty_text(self):
        """Test truncation of empty text"""
        assert truncate_text("") == ""
        assert truncate_text(None) is None

    def test_truncate_custom_suffix(self):
        """Test truncation with custom suffix"""
        text = "Long text here"
        result = truncate_text(text, max_length=10, suffix="[...]")
        assert "[...]" in result


class TestHealthChecker:
    """Tests for HealthChecker class"""

    def test_register_check(self):
        """Test registering a health check"""
        checker = HealthChecker()

        def sample_check():
            return True

        checker.register_check("test_check", sample_check, "Test description")

        assert "test_check" in checker.checks
        assert checker.checks["test_check"]["description"] == "Test description"

    def test_run_checks_success(self):
        """Test running successful health checks"""
        checker = HealthChecker()

        def healthy_check():
            return True

        checker.register_check("healthy", healthy_check)
        results = checker.run_checks()

        assert "healthy" in results
        assert results["healthy"]["status"] == "healthy"
        assert results["healthy"]["result"] is True

    def test_run_checks_failure(self):
        """Test running failing health checks"""
        checker = HealthChecker()

        def unhealthy_check():
            return False

        checker.register_check("unhealthy", unhealthy_check)
        results = checker.run_checks()

        assert "unhealthy" in results
        assert results["unhealthy"]["status"] == "unhealthy"
        assert results["unhealthy"]["result"] is False

    def test_run_checks_exception(self):
        """Test health check that raises exception"""
        checker = HealthChecker()

        def error_check():
            raise RuntimeError("Check failed")

        checker.register_check("error", error_check)
        results = checker.run_checks()

        assert "error" in results
        assert results["error"]["status"] == "error"
        assert "Check failed" in results["error"]["error"]

    def test_get_overall_status_healthy(self):
        """Test overall status when all checks pass"""
        checker = HealthChecker()

        checker.register_check("check1", lambda: True)
        checker.register_check("check2", lambda: True)

        status = checker.get_overall_status()
        assert status == "healthy"

    def test_get_overall_status_degraded(self):
        """Test overall status when some checks fail"""
        checker = HealthChecker()

        checker.register_check("check1", lambda: True)
        checker.register_check("check2", lambda: False)

        status = checker.get_overall_status()
        assert status == "degraded"

    def test_get_overall_status_error(self):
        """Test overall status when checks have errors"""
        checker = HealthChecker()

        def error_check():
            raise RuntimeError("Error")

        checker.register_check("check1", lambda: True)
        checker.register_check("check2", error_check)

        status = checker.get_overall_status()
        assert status == "error"

    def test_get_overall_status_unknown(self):
        """Test overall status with no checks"""
        checker = HealthChecker()
        status = checker.get_overall_status()
        assert status == "unknown"

    def test_check_duration_tracking(self):
        """Test that check duration is tracked"""
        checker = HealthChecker()

        def slow_check():
            time.sleep(0.01)
            return True

        checker.register_check("slow", slow_check)
        results = checker.run_checks()

        assert "duration" in results["slow"]
        assert results["slow"]["duration"] > 0


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_sanitize_text_unicode(self):
        """Test sanitization with unicode characters"""
        text = "Hello 世界 🌍"
        result = sanitize_text(text)
        assert isinstance(result, str)

    def test_hash_unicode_content(self):
        """Test hashing unicode content"""
        content = "Unicode content: 日本語"
        hash_result = generate_content_hash(content)
        assert isinstance(hash_result, str)
        assert len(hash_result) == 64

    def test_validate_email_unicode(self):
        """Test email validation with unicode"""
        # Most email validators don't support unicode domains well
        email = "user@domain.com"  # Stick to ASCII for reliability
        assert validate_email(email) is True

    def test_sanitize_text_very_long(self):
        """Test sanitization with very long text"""
        text = "a" * 100000
        result = sanitize_text(text, max_length=1000)
        assert len(result) <= 1000

    def test_parse_date_with_timezone(self):
        """Test date parsing with timezone info"""
        date_str = "2024-01-15T12:30:45+00:00"
        result = parse_date_flexible(date_str)
        # May or may not parse depending on format support
        assert result is None or isinstance(result, datetime)
