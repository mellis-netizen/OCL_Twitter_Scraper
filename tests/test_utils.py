"""
Unit tests for utils.py module
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os
from datetime import datetime, timezone

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils import (
    validate_url, validate_email, sanitize_text, format_timestamp,
    parse_date_flexible, generate_content_hash, is_content_duplicate,
    HealthChecker
)


class TestUtils(unittest.TestCase):
    """Test cases for utility functions"""
    
    def test_validate_url(self):
        """Test URL validation"""
        # Valid URLs
        self.assertTrue(validate_url("https://example.com"))
        self.assertTrue(validate_url("http://example.com"))
        self.assertTrue(validate_url("https://subdomain.example.com/path"))
        
        # Invalid URLs
        self.assertFalse(validate_url(""))
        self.assertFalse(validate_url("not-a-url"))
        self.assertFalse(validate_url("example.com"))
        # Note: ftp://example.com is actually valid according to urlparse
    
    def test_validate_email(self):
        """Test email validation"""
        # Valid emails
        self.assertTrue(validate_email("test@example.com"))
        self.assertTrue(validate_email("user.name@domain.co.uk"))
        self.assertTrue(validate_email("user+tag@example.org"))
        
        # Invalid emails
        self.assertFalse(validate_email(""))
        self.assertFalse(validate_email("invalid-email"))
        self.assertFalse(validate_email("@example.com"))
        self.assertFalse(validate_email("test@"))
        self.assertFalse(validate_email("test@.com"))
    
    def test_sanitize_text(self):
        """Test text sanitization"""
        # Test control character removal
        text = "Text\x00with\x01control\x02chars"
        sanitized = sanitize_text(text)
        self.assertNotIn('\x00', sanitized)
        self.assertNotIn('\x01', sanitized)
        self.assertNotIn('\x02', sanitized)
        
        # Test whitespace normalization
        text = "Text   with\n\nmultiple\t\tspaces"
        sanitized = sanitize_text(text)
        self.assertNotIn('   ', sanitized)
        self.assertNotIn('\n\n', sanitized)
        self.assertNotIn('\t\t', sanitized)
        
        # Test length limiting
        long_text = "x" * 2000
        sanitized = sanitize_text(long_text, max_length=100)
        self.assertLessEqual(len(sanitized), 100)
        self.assertTrue(sanitized.endswith("..."))
        
        # Test empty/None input
        self.assertEqual(sanitize_text(""), "")
        self.assertEqual(sanitize_text(None), "")
    
    def test_format_timestamp(self):
        """Test timestamp formatting"""
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        # Test with custom format
        formatted = format_timestamp(dt, "%Y-%m-%d %H:%M:%S")
        self.assertEqual(formatted, "2024-01-01 12:00:00")
        
        # Test with default format
        formatted = format_timestamp(dt)
        self.assertIn("2024-01-01", formatted)
        self.assertIn("12:00:00", formatted)
        
        # Test with None
        formatted = format_timestamp(None)
        self.assertIsInstance(formatted, str)
    
    def test_parse_date_flexible(self):
        """Test flexible date parsing"""
        # Test ISO format
        dt = parse_date_flexible("2024-01-01T12:00:00Z")
        self.assertIsInstance(dt, datetime)
        
        # Test common format
        dt = parse_date_flexible("2024-01-01 12:00:00")
        self.assertIsInstance(dt, datetime)
        
        # Test invalid input
        self.assertIsNone(parse_date_flexible(""))
        self.assertIsNone(parse_date_flexible("invalid date"))
        self.assertIsNone(parse_date_flexible(None))
    
    def test_generate_content_hash(self):
        """Test content hash generation"""
        content1 = "Test content"
        content2 = "Test content"
        content3 = "Different content"
        
        hash1 = generate_content_hash(content1)
        hash2 = generate_content_hash(content2)
        hash3 = generate_content_hash(content3)
        
        # Same content should produce same hash
        self.assertEqual(hash1, hash2)
        
        # Different content should produce different hash
        self.assertNotEqual(hash1, hash3)
        
        # Hash should be string
        self.assertIsInstance(hash1, str)
        self.assertEqual(len(hash1), 64)  # SHA-256 hash length
    
    def test_is_content_duplicate(self):
        """Test content duplicate detection"""
        seen_hashes = set()
        content1 = "Test content"
        content2 = "Test content"
        content3 = "Different content"
        
        # First time should not be duplicate
        self.assertFalse(is_content_duplicate(content1, seen_hashes))
        
        # Second time with same content should be duplicate
        self.assertTrue(is_content_duplicate(content2, seen_hashes))
        
        # Different content should not be duplicate
        self.assertFalse(is_content_duplicate(content3, seen_hashes))


class TestHealthChecker(unittest.TestCase):
    """Test cases for HealthChecker class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.health_checker = HealthChecker()
    
    def test_register_check(self):
        """Test health check registration"""
        def test_check():
            return True
        
        self.health_checker.register_check("test", test_check, "Test check")
        
        self.assertIn("test", self.health_checker.checks)
        self.assertEqual(self.health_checker.checks["test"]["function"], test_check)
        self.assertEqual(self.health_checker.checks["test"]["description"], "Test check")
    
    def test_run_checks_success(self):
        """Test running successful health checks"""
        def success_check():
            return True
        
        def failure_check():
            return False
        
        self.health_checker.register_check("success", success_check, "Success check")
        self.health_checker.register_check("failure", failure_check, "Failure check")
        
        results = self.health_checker.run_checks()
        
        self.assertEqual(results["success"]["status"], "healthy")
        self.assertEqual(results["failure"]["status"], "unhealthy")
        self.assertTrue(results["success"]["result"])
        self.assertFalse(results["failure"]["result"])
    
    def test_run_checks_exception(self):
        """Test running health checks that raise exceptions"""
        def exception_check():
            raise ValueError("Test error")
        
        self.health_checker.register_check("exception", exception_check, "Exception check")
        
        results = self.health_checker.run_checks()
        
        self.assertEqual(results["exception"]["status"], "error")
        self.assertFalse(results["exception"]["result"])
        self.assertIn("Test error", results["exception"]["error"])
    
    def test_get_overall_status(self):
        """Test overall status calculation"""
        # Test with no checks
        status = self.health_checker.get_overall_status()
        self.assertEqual(status, "unknown")
        
        # Test with all healthy checks
        def healthy_check():
            return True
        
        self.health_checker.register_check("healthy1", healthy_check, "Healthy 1")
        self.health_checker.register_check("healthy2", healthy_check, "Healthy 2")
        
        status = self.health_checker.get_overall_status()
        self.assertEqual(status, "healthy")
        
        # Test with error check
        def error_check():
            raise Exception("Error")
        
        self.health_checker.register_check("error", error_check, "Error check")
        
        status = self.health_checker.get_overall_status()
        self.assertEqual(status, "error")


if __name__ == '__main__':
    unittest.main()
