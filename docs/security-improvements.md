# Security Improvements - Priority Actions

## CRITICAL Security Fixes Required

### 1. Database Credentials (CRITICAL)

**Current Code** (`src/database.py:19-22`):
```python
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://computer@localhost:5432/tge_monitor'  # HARDCODED USERNAME
)
```

**Fix:**
```python
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is required. "
        "Example: postgresql://user:password@host:port/database"
    )
```

**Impact:** Prevents credential exposure in version control

---

### 2. CORS Configuration (CRITICAL)

**Current Code** (`src/api.py:50-56`):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # DANGEROUS WITH CREDENTIALS
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Fix:**
```python
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '').split(',')
if not ALLOWED_ORIGINS or ALLOWED_ORIGINS == ['']:
    if os.getenv('ENV') == 'production':
        raise RuntimeError("ALLOWED_ORIGINS required in production")
    ALLOWED_ORIGINS = ['http://localhost:3000']  # Dev default

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    max_age=3600
)
```

**Impact:** Prevents CSRF attacks from malicious websites

---

### 3. Input Validation (HIGH)

**Add to `src/schemas.py`:**
```python
from pydantic import BaseModel, Field, validator
import re

class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    aliases: List[str] = Field(default=[], max_items=20)
    tokens: List[str] = Field(default=[], max_items=10)
    exclusions: List[str] = Field(default=[], max_items=50)

    @validator('aliases', 'tokens', 'exclusions', each_item=True)
    def validate_string_items(cls, v):
        if len(v) > 100:
            raise ValueError('Items must be less than 100 characters')
        if not re.match(r'^[a-zA-Z0-9\s\-_\.]+$', v):
            raise ValueError('Invalid characters in input')
        return v

class AlertFilter(BaseModel):
    keywords: List[str] = Field(default=[], max_items=10)

    @validator('keywords', each_item=True)
    def validate_keyword(cls, v):
        if len(v) > 50:
            raise ValueError('Keyword too long')
        if not re.match(r'^[a-zA-Z0-9\s\-_]+$', v):
            raise ValueError('Invalid keyword format')
        return v
```

**Impact:** Prevents injection attacks and DoS via large payloads

---

### 4. SQL Injection Protection (MEDIUM)

**Current Code** (`src/api.py:571-577`):
```python
if filters.keywords:
    keyword_filters = []
    for keyword in filters.keywords:
        keyword_filters.append(Alert.title.ilike(f"%{keyword}%"))
        keyword_filters.append(Alert.content.ilike(f"%{keyword}%"))
```

**Fix:**
```python
if filters.keywords:
    keyword_filters = []
    for keyword in filters.keywords[:10]:  # Limit keywords
        # Escape SQL wildcards
        safe_keyword = keyword.replace('%', '\\%').replace('_', '\\_')
        keyword_filters.append(
            Alert.title.ilike(f"%{safe_keyword}%", escape='\\')
        )
        keyword_filters.append(
            Alert.content.ilike(f"%{safe_keyword}%", escape='\\')
        )
```

**Impact:** Defense-in-depth against SQL injection

---

### 5. Rate Limiting (HIGH)

**Add to public endpoints:**
```python
from fastapi import Request
from fastapi_limiter.depends import RateLimiter

@app.post("/monitoring/trigger")
@limiter.limit("5/hour")  # 5 requests per hour
async def trigger_monitoring_cycle(
    request: Request,
    db: Session = Depends(DatabaseManager.get_db)
):
    # ... existing code
```

**Or use custom rate limiter:**
```python
def check_public_rate_limit(request: Request):
    client_ip = request.client.host
    key = f"public:{client_ip}"
    check_rate_limit(key, limit=10, window=3600)  # 10 per hour
```

---

### 6. Security Headers

**Add middleware:**
```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware import Middleware

middleware = [
    Middleware(
        TrustedHostMiddleware,
        allowed_hosts=os.getenv('ALLOWED_HOSTS', 'localhost').split(',')
    ),
]

app = FastAPI(middleware=middleware)

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

---

### 7. Secrets Management

**Create `.env.example`:**
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/tge_monitor

# Authentication
SECRET_KEY=your-secret-key-here
ADMIN_PASSWORD=your-secure-admin-password

# Security
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
ALLOWED_HOSTS=localhost,yourdomain.com

# Email (Optional)
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
RECIPIENT_EMAIL=alerts@yourdomain.com

# Twitter (Optional)
TWITTER_BEARER_TOKEN=your-bearer-token

# Redis
REDIS_URL=redis://localhost:6379/0

# Environment
ENV=development
```

**Add validation on startup** (`src/api.py`):
```python
@app.on_event("startup")
async def validate_config():
    required_vars = ['DATABASE_URL', 'SECRET_KEY', 'ADMIN_PASSWORD']
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Copy .env.example to .env and fill in values."
        )

    if os.getenv('ENV') == 'production':
        prod_vars = ['ALLOWED_ORIGINS', 'ALLOWED_HOSTS']
        missing_prod = [var for var in prod_vars if not os.getenv(var)]
        if missing_prod:
            raise RuntimeError(
                f"Production environment requires: {', '.join(missing_prod)}"
            )
```

---

## Implementation Checklist

### Phase 1: Critical Fixes (Do First)
- [ ] Remove hardcoded database credentials
- [ ] Fix CORS configuration
- [ ] Add environment variable validation
- [ ] Create `.env.example` file
- [ ] Update deployment docs

### Phase 2: Input Validation (Next)
- [ ] Add Pydantic validators to all schemas
- [ ] Add length limits to string fields
- [ ] Add character whitelist validation
- [ ] Test with malicious inputs

### Phase 3: Security Hardening (Then)
- [ ] Implement rate limiting
- [ ] Add security headers
- [ ] Add SQL wildcard escaping
- [ ] Add request logging
- [ ] Add security audit logging

### Phase 4: Testing (Finally)
- [ ] Write security tests
- [ ] Perform penetration testing
- [ ] Run OWASP ZAP scan
- [ ] Review with security team

---

## Testing Security Fixes

### 1. Test Database Config
```bash
# Should fail without DATABASE_URL
unset DATABASE_URL
python -m src.api

# Should succeed with DATABASE_URL
export DATABASE_URL='postgresql://user:pass@localhost/db'
python -m src.api
```

### 2. Test CORS
```bash
# Should reject cross-origin requests
curl -H "Origin: https://evil.com" \
     -H "Cookie: session=xxx" \
     http://localhost:8000/api/alerts

# Should allow configured origin
curl -H "Origin: https://yourdomain.com" \
     http://localhost:8000/api/alerts
```

### 3. Test Input Validation
```python
# Test with malicious input
response = client.post('/companies', json={
    'name': 'A' * 1000,  # Too long
    'aliases': ['test'] * 100,  # Too many
    'tokens': ['<script>alert(1)</script>']  # XSS attempt
})
assert response.status_code == 422  # Validation error
```

### 4. Test Rate Limiting
```bash
# Should block after limit
for i in {1..20}; do
    curl http://localhost:8000/monitoring/trigger
done
# Expect 429 Too Many Requests
```

---

## Security Best Practices

### For Developers
1. Never commit `.env` files
2. Use environment variables for all secrets
3. Validate all user input
4. Use parameterized queries (SQLAlchemy ORM does this)
5. Keep dependencies updated
6. Run security linters (bandit, safety)

### For DevOps
1. Use secrets management (AWS Secrets Manager, HashiCorp Vault)
2. Enable HTTPS only
3. Use WAF for additional protection
4. Monitor for suspicious activity
5. Regular security audits
6. Rotate credentials regularly

### For Operations
1. Monitor error logs for attacks
2. Set up alerts for failed auth attempts
3. Review access logs regularly
4. Keep systems patched
5. Use intrusion detection systems

---

## Additional Resources

- OWASP Top 10: https://owasp.org/www-project-top-ten/
- FastAPI Security: https://fastapi.tiangolo.com/tutorial/security/
- SQLAlchemy Security: https://docs.sqlalchemy.org/en/14/faq/security.html
- Python Security Best Practices: https://python.readthedocs.io/en/stable/library/security_warnings.html
