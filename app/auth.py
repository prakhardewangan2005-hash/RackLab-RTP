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
    import hmac
    
    token = credentials.credentials
    expected_token = settings.auth_token
    
    # Constant-time comparison
    is_valid = hmac.compare_digest(token, expected_token)
    
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
