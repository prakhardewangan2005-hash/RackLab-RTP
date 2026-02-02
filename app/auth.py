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

## 📝 How to Fix on GitHub

1. Go to your GitHub repository
2. Navigate to `app/auth.py`
3. Click the **pencil icon** (✏️) to edit
4. **Select all and delete** (Ctrl+A, Delete)
5. **Paste the clean code above**
6. Scroll down, click **"Commit changes"**

---

## ⚠️ The Problem

When you copied the code, fancy characters got mixed in:
- **Wrong:** `—` (em dash, Unicode U+270F)
- **Correct:** `-` (regular dash/hyphen)

This happened in comments or strings.

---

## 🎯 After Fixing

1. Wait 1-2 minutes for auto-deploy
2. Or trigger **"Manual Deploy"** in Render
3. Watch the logs

You should now see:
```
==> Starting service
INFO:     Started server process
INFO:     Application startup complete.
==> Your service is live! 🎉
