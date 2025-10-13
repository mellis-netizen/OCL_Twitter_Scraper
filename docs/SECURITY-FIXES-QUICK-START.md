# Security Fixes Quick Start Guide

## 🚨 CRITICAL: Apply These Fixes Immediately

This guide provides copy-paste fixes for the **8 critical security vulnerabilities** found in the OCL Twitter Scraper codebase.

---

## 1. Fix CORS Configuration (2 hours)

**File:** `/src/api.py` (lines 50-57)

### Current Code (INSECURE):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ INSECURE
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Replace With (SECURE):
```python
import os

# Get allowed origins from environment variable
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # ✅ Whitelist only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Specific methods only
    allow_headers=["Content-Type", "Authorization"],  # Specific headers only
    max_age=600,  # Cache preflight for 10 minutes
)
```

### Environment Variable:
```bash
# .env
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

---

## 2. Require ADMIN_PASSWORD (1 hour)

**File:** `/src/auth.py` (lines 359-371)

### Current Code (INSECURE):
```python
admin_password = os.getenv("ADMIN_PASSWORD")
if not admin_password:
    admin_password = secrets.token_urlsafe(16)
    print(f"  Password: {admin_password}")  # ⚠️ Logged
```

### Replace With (SECURE):
```python
admin_password = os.getenv("ADMIN_PASSWORD")
if not admin_password:
    raise ValueError(
        "ADMIN_PASSWORD environment variable is required. "
        "Set it in .env before starting the application."
    )
```

### Environment Variable:
```bash
# .env
ADMIN_PASSWORD=your-secure-password-here-min-16-chars
```

---

## 3. Require SECRET_KEY (1 hour)

**File:** `/src/auth.py` (line 22)

### Current Code (INSECURE):
```python
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))  # ⚠️ Regenerates on restart
```

### Replace With (SECURE):
```python
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError(
        "SECRET_KEY environment variable is required. "
        "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
    )
```

### Generate and Set:
```bash
# Generate secure key
python -c 'import secrets; print(secrets.token_urlsafe(32))'

# Add to .env
SECRET_KEY=your-generated-key-here
```

---

## 4. Add Authentication to Public Endpoints (8 hours)

### Companies Endpoints

**File:** `/src/api.py` (lines 364-429)

#### Create Company (Line 364):
```python
# BEFORE
@app.post("/companies", response_model=CompanyResponse)
async def create_company(
    company_data: CompanyCreate,
    db: Session = Depends(DatabaseManager.get_db),
    current_user: Optional[User] = Depends(optional_user)  # ⚠️ Optional
):

# AFTER
@app.post("/companies", response_model=CompanyResponse)
async def create_company(
    company_data: CompanyCreate,
    db: Session = Depends(DatabaseManager.get_db),
    current_user: User = Depends(get_current_active_user)  # ✅ Required
):
```

#### Update Company (Line 387):
```python
# BEFORE
@app.put("/companies/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: int,
    company_update: CompanyUpdate,
    db: Session = Depends(DatabaseManager.get_db),
    current_user: Optional[User] = Depends(optional_user)  # ⚠️ Optional
):

# AFTER
@app.put("/companies/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: int,
    company_update: CompanyUpdate,
    db: Session = Depends(DatabaseManager.get_db),
    current_user: User = Depends(get_current_active_user)  # ✅ Required
):
```

#### Delete Company (Line 412):
```python
# BEFORE
@app.delete("/companies/{company_id}")
async def delete_company(
    company_id: int,
    db: Session = Depends(DatabaseManager.get_db),
    current_user: Optional[User] = Depends(optional_user)  # ⚠️ Optional
):

# AFTER
@app.delete("/companies/{company_id}")
async def delete_company(
    company_id: int,
    db: Session = Depends(DatabaseManager.get_db),
    current_user: User = Depends(get_current_active_user)  # ✅ Required
):
```

### Feed Endpoints (Similar Changes)

**File:** `/src/api.py` (lines 461-526)

Apply same pattern to:
- `create_feed` (line 461)
- `update_feed` (line 484)
- `delete_feed` (line 509)

### Monitoring Endpoints (Admin Only)

**File:** `/src/api.py` (lines 774-1033)

#### Trigger Scraping (Line 774):
```python
# BEFORE
@app.post("/monitoring/trigger")
async def trigger_monitoring_cycle(db: Session = Depends(DatabaseManager.get_db)):
    # ⚠️ NO authentication

# AFTER
@app.post("/monitoring/trigger")
async def trigger_monitoring_cycle(
    db: Session = Depends(DatabaseManager.get_db),
    current_user: User = Depends(get_current_admin_user)  # ✅ Admin only
):
```

#### Seed Data (Line 759):
```python
# BEFORE
@app.post("/seed-data")
async def seed_database():
    # ⚠️ NO authentication

# AFTER
@app.post("/seed-data")
async def seed_database(
    current_user: User = Depends(get_current_admin_user)  # ✅ Admin only
):
```

---

## 5. Add Input Validation (4 hours)

### Alert Creation

**File:** `/src/api.py` (line 593)

```python
from .validation import InputValidator, ContentSanitizer

@app.post("/alerts", response_model=AlertResponse)
async def create_alert(
    alert_data: AlertCreate,
    db: Session = Depends(DatabaseManager.get_db),
    current_user: User = Depends(get_current_active_user)
):
    # ✅ Validate URL
    if alert_data.source_url:
        url_result = InputValidator.validate_url(alert_data.source_url)
        if not url_result.is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source URL: {', '.join(url_result.errors)}"
            )
        alert_data.source_url = url_result.sanitized_value

    # ✅ Sanitize content
    title_result = InputValidator.validate_string(
        alert_data.title,
        max_length=500,
        allow_empty=False
    )
    if not title_result.is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid title: {', '.join(title_result.errors)}"
        )
    alert_data.title = ContentSanitizer.sanitize_text(title_result.sanitized_value)

    content_result = InputValidator.validate_string(
        alert_data.content,
        max_length=10000,
        allow_empty=False
    )
    if not content_result.is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content: {', '.join(content_result.errors)}"
        )
    alert_data.content = ContentSanitizer.sanitize_text(content_result.sanitized_value)

    # Continue with creation
    alert = Alert(**alert_data.dict(), user_id=current_user.id)
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return AlertResponse.from_orm(alert)
```

### Keyword Search Filtering

**File:** `/src/api.py` (line 565)

```python
from .validation import InputValidator

if filters.keywords:
    keyword_filters = []
    for keyword in filters.keywords:
        # ✅ Validate keyword
        result = InputValidator.validate_string(
            keyword,
            max_length=100,
            allow_empty=False
        )
        if not result.is_valid:
            continue  # Skip invalid keywords

        safe_keyword = result.sanitized_value
        # SQLAlchemy handles parameterization
        keyword_filters.append(Alert.title.ilike(f"%{safe_keyword}%"))
        keyword_filters.append(Alert.content.ilike(f"%{safe_keyword}%"))

    if keyword_filters:
        query = query.filter(or_(*keyword_filters))
```

---

## 6. Remove Frontend Credential Exposure (15 minutes)

**File:** `/frontend/src/components/Login.tsx` (line 85)

### Remove This:
```typescript
<div className="mt-6 text-center text-sm text-gray-400">
  <p>Default credentials: admin / adminpassword</p>  {/* ⚠️ REMOVE */}
</div>
```

---

## 7. Fix Frontend Authentication (4 hours)

**Option A: Re-enable Authentication (Recommended)**

**File:** `/frontend/src/hooks/useAuth.tsx`

Replace entire file with proper authentication:

```typescript
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import apiClient from '../services/api';
import wsClient from '../services/websocket';
import type { User, LoginRequest, UserCreate } from '../types/api';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => void;
  register: (data: UserCreate) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const isAuthenticated = user !== null;

  // Load user on mount
  useEffect(() => {
    const loadUser = async () => {
      const token = localStorage.getItem('auth_token');
      if (token) {
        try {
          const currentUser = await apiClient.getCurrentUser();
          setUser(currentUser);
        } catch (error) {
          console.error('Failed to load user:', error);
          localStorage.removeItem('auth_token');
        }
      }
      setIsLoading(false);
    };

    loadUser();
  }, []);

  // WebSocket connection
  useEffect(() => {
    if (user) {
      const token = localStorage.getItem('auth_token');
      wsClient.connect(token || '', {
        onConnect: () => console.log('WebSocket connected'),
        onDisconnect: () => console.log('WebSocket disconnected'),
      });
    }

    return () => {
      wsClient.disconnect();
    };
  }, [user]);

  const login = async (credentials: LoginRequest) => {
    const tokenData = await apiClient.login(credentials);
    apiClient.setAuthToken(tokenData.access_token);
    const currentUser = await apiClient.getCurrentUser();
    setUser(currentUser);
  };

  const logout = () => {
    apiClient.clearAuth();
    setUser(null);
    wsClient.disconnect();
  };

  const register = async (data: UserCreate) => {
    await apiClient.register(data);
    // Auto-login after registration
    await login({ username: data.username, password: data.password });
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated,
        login,
        logout,
        register,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
```

**Option B: Document Public Access (If Keeping Current)**

Add prominent warning to dashboard:

```typescript
// Add to Dashboard.tsx
<div className="bg-red-900 bg-opacity-30 border border-red-700 rounded-lg p-4 mb-6">
  <div className="flex items-center gap-3">
    <div className="text-red-400 text-2xl">⚠️</div>
    <div>
      <h3 className="text-red-300 font-semibold">Public Access Mode</h3>
      <p className="text-red-200 text-sm">
        Authentication is disabled. This application is accessible to anyone with network access.
        DO NOT use in production without enabling authentication.
      </p>
    </div>
  </div>
</div>
```

---

## 8. Add Security Headers (1 hour)

**File:** `/src/api.py` (after CORS middleware)

```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

# Trusted host middleware (prevent host header attacks)
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)

# Force HTTPS in production
if os.getenv("ENVIRONMENT") == "production":
    app.add_middleware(HTTPSRedirectMiddleware)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)

    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"

    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # XSS Protection
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Content Security Policy
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' ws: wss:;"
    )

    # Force HTTPS (production only)
    if os.getenv("ENVIRONMENT") == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response
```

---

## Quick Deploy Checklist

Before deploying with these fixes:

### 1. Environment Variables
```bash
# Required environment variables
cat > .env << EOF
# Authentication
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
ADMIN_PASSWORD=your-secure-admin-password-min-16-chars
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@yourdomain.com

# API Configuration
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
ALLOWED_HOSTS=yourdomain.com,app.yourdomain.com

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/tge_monitor

# Redis
REDIS_URL=redis://localhost:6379/0

# Environment
ENVIRONMENT=production
EOF
```

### 2. Test Security Fixes
```bash
# Test 1: CORS should reject evil-site.com
curl -X POST http://localhost:8000/companies \
  -H "Origin: https://evil-site.com" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test"}' \
  && echo "❌ CORS NOT FIXED" || echo "✅ CORS FIXED"

# Test 2: Should require authentication
curl http://localhost:8000/monitoring/trigger -X POST \
  && echo "❌ AUTH NOT REQUIRED" || echo "✅ AUTH REQUIRED"

# Test 3: Should validate input
curl http://localhost:8000/alerts \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"<script>alert(1)</script>","content":"test"}' \
  && echo "Check if XSS was sanitized"
```

### 3. Restart Application
```bash
# Kill existing processes
pkill -f "uvicorn.*api:app"

# Start with new environment
uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
```

---

## Verification

After applying fixes, verify:

- [ ] Application starts without auto-generating passwords
- [ ] CORS rejects unauthorized origins
- [ ] All endpoints require authentication
- [ ] Input validation blocks XSS/SQL injection attempts
- [ ] Security headers present in responses
- [ ] Frontend authentication works (or warning displayed)

---

## Time Estimates

- **Fix 1 (CORS)**: 30 minutes
- **Fix 2 (Admin Password)**: 15 minutes
- **Fix 3 (Secret Key)**: 15 minutes
- **Fix 4 (Authentication)**: 4 hours
- **Fix 5 (Validation)**: 2 hours
- **Fix 6 (Credentials)**: 5 minutes
- **Fix 7 (Frontend Auth)**: 2 hours
- **Fix 8 (Security Headers)**: 30 minutes

**Total: ~9-10 hours** for critical security fixes

---

## Need Help?

If you encounter issues:

1. Check logs: `tail -f logs/app.log`
2. Verify environment variables: `env | grep -E "(SECRET|ADMIN|ALLOWED)"`
3. Test database connection: `python -c "from src.database import DatabaseManager; print(DatabaseManager.check_connection())"`
4. Refer to full analysis: `docs/code-quality-security-analysis.md`

---

**Generated by Code Quality Analyzer**
**Date:** 2025-10-13
