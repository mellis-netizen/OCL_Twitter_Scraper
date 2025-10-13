"""
Production-Grade Data Validation and Sanitization
Provides comprehensive input validation, XSS/SQL injection protection, and content sanitization
"""

import re
import html
import logging
import bleach
from typing import Any, Dict, List, Optional, Union, Type
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation strictness levels"""
    STRICT = "strict"
    MODERATE = "moderate"
    PERMISSIVE = "permissive"


@dataclass
class ValidationResult:
    """Result of validation"""
    is_valid: bool
    sanitized_value: Any
    errors: List[str]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'is_valid': self.is_valid,
            'sanitized_value': self.sanitized_value,
            'errors': self.errors,
            'warnings': self.warnings
        }


class InputValidator:
    """Validates and sanitizes various types of input"""

    # Common injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|\#|\/\*|\*\/)",
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)",
        r"(;.*\b(SELECT|INSERT|UPDATE|DELETE)\b)",
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bSCRIPT\b.*>)",
    ]

    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
        r"<object",
        r"<embed",
        r"<applet",
    ]

    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$()]",
        r"\$\{.*\}",
        r"\$\(.*\)",
    ]

    @staticmethod
    def validate_string(
        value: str,
        min_length: int = 0,
        max_length: int = 10000,
        pattern: Optional[str] = None,
        allow_empty: bool = True,
        strip: bool = True
    ) -> ValidationResult:
        """
        Validate and sanitize string input

        Args:
            value: String to validate
            min_length: Minimum allowed length
            max_length: Maximum allowed length
            pattern: Optional regex pattern to match
            allow_empty: Whether to allow empty strings
            strip: Whether to strip whitespace

        Returns:
            ValidationResult
        """
        errors = []
        warnings = []

        if not isinstance(value, str):
            errors.append(f"Expected string, got {type(value).__name__}")
            return ValidationResult(False, None, errors, warnings)

        # Strip if requested
        sanitized = value.strip() if strip else value

        # Check empty
        if not sanitized and not allow_empty:
            errors.append("Empty string not allowed")
            return ValidationResult(False, sanitized, errors, warnings)

        # Check length
        if len(sanitized) < min_length:
            errors.append(f"String too short (min: {min_length}, got: {len(sanitized)})")

        if len(sanitized) > max_length:
            errors.append(f"String too long (max: {max_length}, got: {len(sanitized)})")
            sanitized = sanitized[:max_length]
            warnings.append(f"String truncated to {max_length} characters")

        # Check pattern if provided
        if pattern and sanitized:
            if not re.match(pattern, sanitized):
                errors.append(f"String does not match required pattern")

        # Check for dangerous patterns
        if InputValidator._contains_sql_injection(sanitized):
            errors.append("Potential SQL injection detected")

        if InputValidator._contains_xss(sanitized):
            errors.append("Potential XSS attack detected")

        is_valid = len(errors) == 0

        return ValidationResult(is_valid, sanitized, errors, warnings)

    @staticmethod
    def validate_email(email: str) -> ValidationResult:
        """Validate email address"""
        errors = []
        warnings = []

        # Basic email regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        sanitized = email.strip().lower()

        if not re.match(email_pattern, sanitized):
            errors.append("Invalid email format")

        # Check for suspicious patterns
        if any(char in sanitized for char in ['<', '>', ';', '"', "'"]):
            errors.append("Email contains invalid characters")

        is_valid = len(errors) == 0

        return ValidationResult(is_valid, sanitized, errors, warnings)

    @staticmethod
    def validate_url(url: str, allowed_schemes: Optional[List[str]] = None) -> ValidationResult:
        """
        Validate URL

        Args:
            url: URL to validate
            allowed_schemes: List of allowed schemes (default: ['http', 'https'])

        Returns:
            ValidationResult
        """
        errors = []
        warnings = []

        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']

        sanitized = url.strip()

        try:
            parsed = urlparse(sanitized)

            # Check scheme
            if parsed.scheme not in allowed_schemes:
                errors.append(f"Invalid URL scheme: {parsed.scheme}")

            # Check netloc (domain)
            if not parsed.netloc:
                errors.append("URL missing domain")

            # Check for dangerous patterns
            if 'javascript:' in sanitized.lower():
                errors.append("JavaScript URLs not allowed")

            # Check for suspicious patterns in query parameters
            if parsed.query:
                query_params = parse_qs(parsed.query)
                for key, values in query_params.items():
                    for value in values:
                        if InputValidator._contains_xss(value):
                            errors.append(f"Potential XSS in query parameter: {key}")

        except Exception as e:
            errors.append(f"Invalid URL format: {str(e)}")

        is_valid = len(errors) == 0

        return ValidationResult(is_valid, sanitized, errors, warnings)

    @staticmethod
    def validate_integer(
        value: Any,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None
    ) -> ValidationResult:
        """Validate integer"""
        errors = []
        warnings = []

        try:
            sanitized = int(value)
        except (ValueError, TypeError):
            errors.append(f"Cannot convert to integer: {value}")
            return ValidationResult(False, None, errors, warnings)

        if min_value is not None and sanitized < min_value:
            errors.append(f"Value too small (min: {min_value}, got: {sanitized})")

        if max_value is not None and sanitized > max_value:
            errors.append(f"Value too large (max: {max_value}, got: {sanitized})")

        is_valid = len(errors) == 0

        return ValidationResult(is_valid, sanitized, errors, warnings)

    @staticmethod
    def validate_float(
        value: Any,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> ValidationResult:
        """Validate float"""
        errors = []
        warnings = []

        try:
            sanitized = float(value)
        except (ValueError, TypeError):
            errors.append(f"Cannot convert to float: {value}")
            return ValidationResult(False, None, errors, warnings)

        if min_value is not None and sanitized < min_value:
            errors.append(f"Value too small (min: {min_value}, got: {sanitized})")

        if max_value is not None and sanitized > max_value:
            errors.append(f"Value too large (max: {max_value}, got: {sanitized})")

        is_valid = len(errors) == 0

        return ValidationResult(is_valid, sanitized, errors, warnings)

    @staticmethod
    def validate_datetime(value: Any, format: str = "%Y-%m-%d %H:%M:%S") -> ValidationResult:
        """Validate datetime"""
        errors = []
        warnings = []

        if isinstance(value, datetime):
            return ValidationResult(True, value, errors, warnings)

        if isinstance(value, str):
            try:
                sanitized = datetime.strptime(value, format)
                return ValidationResult(True, sanitized, errors, warnings)
            except ValueError as e:
                errors.append(f"Invalid datetime format: {str(e)}")

        errors.append(f"Cannot convert to datetime: {type(value).__name__}")
        return ValidationResult(False, None, errors, warnings)

    @staticmethod
    def _contains_sql_injection(value: str) -> bool:
        """Check if string contains SQL injection patterns"""
        for pattern in InputValidator.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"SQL injection pattern detected: {pattern}")
                return True
        return False

    @staticmethod
    def _contains_xss(value: str) -> bool:
        """Check if string contains XSS patterns"""
        for pattern in InputValidator.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"XSS pattern detected: {pattern}")
                return True
        return False

    @staticmethod
    def _contains_command_injection(value: str) -> bool:
        """Check if string contains command injection patterns"""
        for pattern in InputValidator.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, value):
                logger.warning(f"Command injection pattern detected: {pattern}")
                return True
        return False


class ContentSanitizer:
    """Sanitizes content to remove dangerous elements"""

    # Allowed HTML tags for user content
    ALLOWED_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'code', 'pre'
    ]

    # Allowed attributes for HTML tags
    ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title'],
        '*': ['class']
    }

    @staticmethod
    def sanitize_html(html_content: str, strict: bool = True) -> str:
        """
        Sanitize HTML content

        Args:
            html_content: HTML to sanitize
            strict: If True, use strict cleaning. If False, allow more tags

        Returns:
            Sanitized HTML
        """
        if strict:
            # Very strict: remove all HTML
            sanitized = bleach.clean(
                html_content,
                tags=[],
                attributes={},
                strip=True
            )
        else:
            # Allow safe tags
            sanitized = bleach.clean(
                html_content,
                tags=ContentSanitizer.ALLOWED_TAGS,
                attributes=ContentSanitizer.ALLOWED_ATTRIBUTES,
                strip=True
            )

        return sanitized

    @staticmethod
    def sanitize_text(text: str) -> str:
        """
        Sanitize plain text

        Args:
            text: Text to sanitize

        Returns:
            Sanitized text
        """
        # HTML escape
        sanitized = html.escape(text)

        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')

        # Normalize whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized)

        return sanitized.strip()

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent path traversal

        Args:
            filename: Filename to sanitize

        Returns:
            Safe filename
        """
        # Remove path components
        filename = filename.split('/')[-1].split('\\')[-1]

        # Remove dangerous characters
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

        # Prevent hidden files
        if filename.startswith('.'):
            filename = '_' + filename[1:]

        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:250] + ('.' + ext if ext else '')

        return filename or 'untitled'

    @staticmethod
    def sanitize_sql_parameter(value: str) -> str:
        """
        Sanitize SQL parameter (note: use parameterized queries instead!)

        Args:
            value: Value to sanitize

        Returns:
            Sanitized value
        """
        # Escape single quotes
        sanitized = value.replace("'", "''")

        # Remove comments
        sanitized = re.sub(r'--.*$', '', sanitized, flags=re.MULTILINE)
        sanitized = re.sub(r'/\*.*?\*/', '', sanitized, flags=re.DOTALL)

        return sanitized

    @staticmethod
    def sanitize_json(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize JSON data recursively

        Args:
            data: Dictionary to sanitize

        Returns:
            Sanitized dictionary
        """
        sanitized = {}

        for key, value in data.items():
            # Sanitize key
            safe_key = ContentSanitizer.sanitize_text(str(key))

            # Sanitize value based on type
            if isinstance(value, str):
                safe_value = ContentSanitizer.sanitize_text(value)
            elif isinstance(value, dict):
                safe_value = ContentSanitizer.sanitize_json(value)
            elif isinstance(value, list):
                safe_value = [
                    ContentSanitizer.sanitize_text(str(item)) if isinstance(item, str)
                    else ContentSanitizer.sanitize_json(item) if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                safe_value = value

            sanitized[safe_key] = safe_value

        return sanitized


class SchemaValidator:
    """Validates data against schemas"""

    @staticmethod
    def validate_dict_schema(
        data: Dict[str, Any],
        schema: Dict[str, Type],
        required_fields: Optional[List[str]] = None
    ) -> ValidationResult:
        """
        Validate dictionary against schema

        Args:
            data: Dictionary to validate
            schema: Schema defining expected types
            required_fields: List of required field names

        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        sanitized = {}

        if required_fields is None:
            required_fields = list(schema.keys())

        # Check required fields
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # Validate each field
        for field, expected_type in schema.items():
            if field not in data:
                continue

            value = data[field]

            # Type check
            if not isinstance(value, expected_type):
                errors.append(
                    f"Field '{field}' has wrong type: expected {expected_type.__name__}, "
                    f"got {type(value).__name__}"
                )
                continue

            # Additional validation based on type
            if expected_type == str:
                result = InputValidator.validate_string(value)
                if not result.is_valid:
                    errors.extend([f"{field}: {err}" for err in result.errors])
                sanitized[field] = result.sanitized_value
            else:
                sanitized[field] = value

        is_valid = len(errors) == 0

        return ValidationResult(is_valid, sanitized, errors, warnings)


# Convenience functions
def validate_user_input(
    value: str,
    input_type: str = "string",
    **kwargs
) -> ValidationResult:
    """
    Convenience function to validate user input

    Args:
        value: Value to validate
        input_type: Type of input (string, email, url, integer, float)
        **kwargs: Additional validation parameters

    Returns:
        ValidationResult
    """
    if input_type == "email":
        return InputValidator.validate_email(value)
    elif input_type == "url":
        return InputValidator.validate_url(value, **kwargs)
    elif input_type == "integer":
        return InputValidator.validate_integer(value, **kwargs)
    elif input_type == "float":
        return InputValidator.validate_float(value, **kwargs)
    else:
        return InputValidator.validate_string(value, **kwargs)


def sanitize_user_content(content: str, content_type: str = "text") -> str:
    """
    Convenience function to sanitize user content

    Args:
        content: Content to sanitize
        content_type: Type of content (text, html, filename)

    Returns:
        Sanitized content
    """
    if content_type == "html":
        return ContentSanitizer.sanitize_html(content, strict=False)
    elif content_type == "filename":
        return ContentSanitizer.sanitize_filename(content)
    else:
        return ContentSanitizer.sanitize_text(content)
