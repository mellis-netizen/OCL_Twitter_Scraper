"""
Security fixes verification tests
Tests for critical security improvements in auth.py and database.py
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestAdminPasswordSecurity:
    """Test admin password security requirements"""

    @patch('src.auth.os.getenv')
    @patch('src.auth.logging.getLogger')
    def test_admin_password_required(self, mock_logger, mock_getenv):
        """Test that admin password is required and fails without it"""
        from src.auth import create_admin_user_if_not_exists

        # Mock environment variables
        def getenv_side_effect(key, default=None):
            env_vars = {
                'ADMIN_USERNAME': 'admin',
                'ADMIN_EMAIL': 'admin@test.com',
                'ADMIN_PASSWORD': None  # Missing password
            }
            return env_vars.get(key, default)

        mock_getenv.side_effect = getenv_side_effect
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Should raise RuntimeError when password is missing
        with pytest.raises(RuntimeError) as exc_info:
            create_admin_user_if_not_exists(mock_db)

        assert "ADMIN_PASSWORD environment variable is required" in str(exc_info.value)
        assert "security reasons" in str(exc_info.value)

    @patch('src.auth.os.getenv')
    @patch('src.auth.logging.getLogger')
    def test_admin_password_length_validation(self, mock_logger, mock_getenv):
        """Test that admin password must be at least 12 characters"""
        from src.auth import create_admin_user_if_not_exists

        # Mock environment variables with weak password
        def getenv_side_effect(key, default=None):
            env_vars = {
                'ADMIN_USERNAME': 'admin',
                'ADMIN_EMAIL': 'admin@test.com',
                'ADMIN_PASSWORD': 'weak123'  # Too short
            }
            return env_vars.get(key, default)

        mock_getenv.side_effect = getenv_side_effect
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Should raise ValueError for weak password
        with pytest.raises(ValueError) as exc_info:
            create_admin_user_if_not_exists(mock_db)

        assert "at least 12 characters long" in str(exc_info.value)


class TestPasswordVerificationSecurity:
    """Test password verification error handling"""

    def test_password_verification_invalid_hash(self):
        """Test that invalid hash format is handled gracefully"""
        from src.auth import AuthManager

        # Invalid hash should return False, not raise
        result = AuthManager.verify_password("test_password", "invalid_hash_format")
        assert result is False

    def test_password_verification_corrupted_hash(self):
        """Test that corrupted hash is detected"""
        from src.auth import AuthManager

        # Corrupted bcrypt hash
        corrupted_hash = "$2b$12$invalid"
        result = AuthManager.verify_password("test_password", corrupted_hash)
        assert result is False

    def test_password_verification_valid(self):
        """Test that valid password verification still works"""
        from src.auth import AuthManager

        password = "test_secure_password_123"
        hashed = AuthManager.hash_password(password)

        # Should verify correctly
        assert AuthManager.verify_password(password, hashed) is True
        assert AuthManager.verify_password("wrong_password", hashed) is False


class TestSQLiteProductionCheck:
    """Test SQLite production environment check"""

    @patch('src.database.os.getenv')
    def test_sqlite_production_fails(self, mock_getenv):
        """Test that SQLite fails in production environment"""
        # Set production environment
        def getenv_side_effect(key, default=None):
            if key == 'ENV':
                return 'production'
            if key == 'DATABASE_URL':
                return 'sqlite:///test.db'
            if key == 'REDIS_URL':
                return 'redis://localhost:6379/0'
            return default

        mock_getenv.side_effect = getenv_side_effect

        # Should raise RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            # Re-import to trigger the engine creation with new env vars
            import importlib
            import src.database
            importlib.reload(src.database)

        assert "SQLite is not supported in production" in str(exc_info.value)

    @patch('src.database.os.getenv')
    @patch('src.database.logger')
    def test_sqlite_development_warns(self, mock_logger, mock_getenv):
        """Test that SQLite in development shows warning"""
        # Set development environment
        def getenv_side_effect(key, default=None):
            if key == 'ENV':
                return 'development'
            if key == 'DATABASE_URL':
                return 'sqlite:///test.db'
            if key == 'REDIS_URL':
                return 'redis://localhost:6379/0'
            return default

        mock_getenv.side_effect = getenv_side_effect

        # Should log warnings but not fail
        import importlib
        import src.database
        importlib.reload(src.database)

        # Check that warning was logged
        warning_calls = [call for call in mock_logger.warning.call_args_list
                        if 'SQLite' in str(call)]
        assert len(warning_calls) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
