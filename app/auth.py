"""
Simple token-based authentication for API endpoints.
Production-ready with secure token comparison.
"""

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)
security = HTTPBearer()


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> bool:
    """
    Verify bearer token against configured AUTH_TOKEN.
    Uses constant-time comparison to prevent timing attacks.
    """
    import secrets
    
    token = credentials.credentials
    expected_token = settings.auth_token
    
    # Constant-time comparison
    is_valid = secrets.compare_digest(token, expected_token)
    
    if not is_valid:
        logger.warning("Invalid authentication token attempted", extra={
            "token_prefix": token[:8] if len(token) >= 8 else "***"
        })
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return True
```

---

## 📝 Steps to Fix

### 1. Update requirements.txt on GitHub

1. Go to your GitHub repository
2. Click **`requirements.txt`**
3. Click the **pencil icon** (✏️)
4. Replace with the minimal version above
5. Commit changes

### 2. Update app/auth.py on GitHub

1. Navigate to `app/auth.py` in GitHub
2. Click the **pencil icon** (✏️)
3. Replace entire content with the code above
4. Commit changes

### 3. Trigger Redeploy

Wait 1-2 minutes or click **"Manual Deploy"** on Render

---

## 🎯 Alternative: Use Even Simpler Requirements

If it still fails, try this **absolute minimum**:
```
fastapi
uvicorn
jinja2
pydantic
pydantic-settings
sqlalchemy
python-dotenv
slowapi
