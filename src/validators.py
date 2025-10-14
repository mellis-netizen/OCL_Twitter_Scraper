"""
Enhanced Input Validation for TGE Monitor API
Pydantic validators to prevent injection attacks and ensure data integrity
"""

from pydantic import validator, constr, conint, confloat, Field
from typing import List, Optional
import re


# Validation patterns
URL_PATTERN = re.compile(r'^https?://')
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{3,50}$')
SAFE_STRING_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_.,!?@#$%&*()+=\[\]{}:;\'"/\\]+$')


def validate_url(url: str) -> str:
    """Validate and sanitize URL"""
    if not url:
        raise ValueError("URL cannot be empty")

    if not URL_PATTERN.match(url):
        raise ValueError("URL must start with http:// or https://")

    if len(url) > 2048:
        raise ValueError("URL too long (max 2048 characters)")

    # Check for suspicious patterns
    suspicious = ['javascript:', 'data:', 'vbscript:', 'file:', '<script']
    if any(pattern in url.lower() for pattern in suspicious):
        raise ValueError("URL contains suspicious content")

    return url


def validate_email(email: str) -> str:
    """Validate email format"""
    if not email:
        raise ValueError("Email cannot be empty")

    if not EMAIL_PATTERN.match(email):
        raise ValueError("Invalid email format")

    if len(email) > 254:
        raise ValueError("Email too long (max 254 characters)")

    return email.lower()


def validate_username(username: str) -> str:
    """Validate username format"""
    if not username:
        raise ValueError("Username cannot be empty")

    if not USERNAME_PATTERN.match(username):
        raise ValueError(
            "Username must be 3-50 characters and contain only "
            "letters, numbers, hyphens, and underscores"
        )

    return username


def validate_safe_string(text: str, max_length: int = 1000, field_name: str = "Text") -> str:
    """Validate string contains no malicious content"""
    if not text:
        return text

    if len(text) > max_length:
        raise ValueError(f"{field_name} too long (max {max_length} characters)")

    # Check for XSS patterns
    xss_patterns = ['<script', '<iframe', '<object', '<embed', 'javascript:', 'onerror=', 'onload=']
    text_lower = text.lower()
    if any(pattern in text_lower for pattern in xss_patterns):
        raise ValueError(f"{field_name} contains potentially malicious content")

    return text


def validate_keyword_list(keywords: List[str]) -> List[str]:
    """Validate list of keywords"""
    if not keywords:
        return keywords

    if len(keywords) > 100:
        raise ValueError("Too many keywords (max 100)")

    validated = []
    for keyword in keywords:
        if not keyword or len(keyword) < 2:
            continue  # Skip empty or too short keywords

        if len(keyword) > 100:
            raise ValueError(f"Keyword too long: {keyword[:50]}... (max 100 characters)")

        # Remove SQL wildcards and special characters
        cleaned = keyword.replace('%', '').replace('_', '').replace('\\', '')
        validated.append(cleaned)

    return validated


def validate_confidence_score(score: float) -> float:
    """Validate confidence score is between 0 and 1"""
    if not 0 <= score <= 1:
        raise ValueError("Confidence score must be between 0 and 1")
    return round(score, 4)


def validate_priority(priority: str) -> str:
    """Validate priority level"""
    allowed = ['low', 'medium', 'high', 'critical']
    if priority and priority.lower() not in allowed:
        raise ValueError(f"Priority must be one of: {', '.join(allowed)}")
    return priority.lower() if priority else 'medium'


def validate_pagination(offset: int, limit: int) -> tuple:
    """Validate pagination parameters"""
    if offset < 0:
        raise ValueError("Offset cannot be negative")

    if limit < 1:
        raise ValueError("Limit must be at least 1")

    if limit > 1000:
        raise ValueError("Limit cannot exceed 1000")

    return offset, limit


def validate_date_range(from_date: Optional[str], to_date: Optional[str]) -> tuple:
    """Validate date range"""
    from datetime import datetime

    if from_date:
        try:
            from_dt = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("Invalid from_date format. Use ISO 8601 format.")
    else:
        from_dt = None

    if to_date:
        try:
            to_dt = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("Invalid to_date format. Use ISO 8601 format.")
    else:
        to_dt = None

    if from_dt and to_dt and from_dt > to_dt:
        raise ValueError("from_date cannot be after to_date")

    return from_dt, to_dt


# Type aliases for common constrained types
SafeString = constr(min_length=1, max_length=1000, strip_whitespace=True)
ShortString = constr(min_length=1, max_length=255, strip_whitespace=True)
LongString = constr(min_length=1, max_length=5000, strip_whitespace=True)
UrlString = constr(regex=r'^https?://', max_length=2048)
EmailString = constr(regex=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', max_length=254)
UsernameString = constr(regex=r'^[a-zA-Z0-9_-]{3,50}$')

PositiveInt = conint(gt=0)
NonNegativeInt = conint(ge=0)
PaginationLimit = conint(ge=1, le=1000)
PaginationOffset = conint(ge=0)

ConfidenceScore = confloat(ge=0.0, le=1.0)
PercentageFloat = confloat(ge=0.0, le=100.0)
