"""
Unit tests for email_notifier.py module
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from email_notifier import EmailNotifier


class TestEmailNotifier(unittest.TestCase):
    """Test cases for email notifier functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'EMAIL_USER': 'test@example.com',
            'EMAIL_PASSWORD': 'testpass',
            'RECIPIENT_EMAIL': 'recipient@example.com',
            'SMTP_SERVER': 'smtp.gmail.com',
            'SMTP_PORT': '587'
        })
        self.env_patcher.start()
    
    def tearDown(self):
        """Clean up after tests"""
        self.env_patcher.stop()
    
    def test_email_validation(self):
        """Test email address validation"""
        notifier = EmailNotifier()
        
        # Valid emails
        self.assertTrue(notifier._validate_email("test@example.com"))
        self.assertTrue(notifier._validate_email("user.name@domain.co.uk"))
        
        # Invalid emails
        self.assertFalse(notifier._validate_email("invalid-email"))
        self.assertFalse(notifier._validate_email("@example.com"))
        self.assertFalse(notifier._validate_email("test@"))
        self.assertFalse(notifier._validate_email(""))
        # Test None handling separately since it causes TypeError
        try:
            notifier._validate_email(None)
            self.fail("Expected TypeError for None input")
        except TypeError:
            pass
    
    def test_header_sanitization(self):
        """Test email header sanitization"""
        notifier = EmailNotifier()
        
        # Test newline removal
        header = "Subject\nwith\nnewlines"
        sanitized = notifier._sanitize_header(header)
        self.assertNotIn('\n', sanitized)
        self.assertNotIn('\r', sanitized)
        
        # Test length limiting
        long_header = "x" * 300
        sanitized = notifier._sanitize_header(long_header)
        self.assertLessEqual(len(sanitized), 200)
        
        # Test None/empty input
        self.assertEqual(notifier._sanitize_header(None), "")
        self.assertEqual(notifier._sanitize_header(""), "")
    
    def test_content_sanitization(self):
        """Test email content sanitization"""
        notifier = EmailNotifier()
        
        # Test control character removal
        content = "Text\x00with\x01control\x02chars"
        sanitized = notifier._sanitize_content(content)
        self.assertNotIn('\x00', sanitized)
        self.assertNotIn('\x01', sanitized)
        self.assertNotIn('\x02', sanitized)
        
        # Test length limiting
        long_content = "x" * (1024 * 1024 + 1000)  # Over 1MB
        sanitized = notifier._sanitize_content(long_content)
        self.assertLessEqual(len(sanitized), 1024 * 1024)
        
        # Test None/empty input
        self.assertEqual(notifier._sanitize_content(None), "")
        self.assertEqual(notifier._sanitize_content(""), "")
    
    def test_email_config_validation(self):
        """Test email configuration validation"""
        notifier = EmailNotifier()
        
        # Should be valid with mocked environment
        self.assertTrue(notifier._validate_email_config())
    
    def test_email_config_validation_invalid(self):
        """Test email configuration validation with invalid config"""
        # Create notifier with invalid config
        notifier = EmailNotifier()
        notifier.email_user = ''
        notifier.email_password = ''
        notifier.recipient_email = ''
        notifier.smtp_server = ''
        notifier.smtp_port = 0
        
        self.assertFalse(notifier._validate_email_config())
    
    def test_generate_email_subject(self):
        """Test email subject generation"""
        notifier = EmailNotifier()
        
        # Test with news alerts
        news_alerts = [{"title": "Test News", "mentioned_companies": ["Arbitrum"]}]
        subject = notifier._generate_email_subject(news_alerts, [], {})
        self.assertIn("TGE Alert", subject)
        self.assertIn("Arbitrum", subject)
        
        # Test with multiple alerts
        news_alerts = [{"title": "Test 1"}, {"title": "Test 2"}]
        subject = notifier._generate_email_subject(news_alerts, [], {})
        self.assertIn("2 TGE Alerts", subject)
        
        # Test with no alerts
        subject = notifier._generate_email_subject([], [], {})
        self.assertIn("No alerts", subject)
    
    def test_news_item_from_alert(self):
        """Test news item extraction from alert"""
        notifier = EmailNotifier()
        
        # Test flat alert structure
        alert = {
            "title": "Test Title",
            "link": "https://example.com",
            "summary": "Test summary",
            "published": "2024-01-01",
            "source": "example.com"
        }
        
        item = notifier._news_item_from_alert(alert)
        self.assertEqual(item["title"], "Test Title")
        self.assertEqual(item["link"], "https://example.com")
        self.assertEqual(item["source_name"], "example.com")
        
        # Test nested alert structure
        alert = {
            "article": {
                "title": "Nested Title",
                "link": "https://nested.com",
                "summary": "Nested summary",
                "published": "2024-01-01",
                "source_name": "nested.com"
            }
        }
        
        item = notifier._news_item_from_alert(alert)
        self.assertEqual(item["title"], "Nested Title")
        self.assertEqual(item["link"], "https://nested.com")


if __name__ == '__main__':
    unittest.main()
