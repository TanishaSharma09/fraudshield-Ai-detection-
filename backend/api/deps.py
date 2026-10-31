"""FraudShield AI - Authentication Dependencies & Role-Based Permissions.

Provides reusable FastAPI route dependencies:
- Bearer token extraction and validation via HTTPBearer.
- Role-based access control (RBAC) enforcing ADMIN and ANALYST privileges.
- Standard HTTP 401 Unauthorized and HTTP 403 Forbidden responses.
"""

from typing import Any
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.core.security import (
    decode_access_token,
    TokenExpiredError,
    TokenRevokedError,
    TokenValidationError,
)
from backend.services.auth_service import get_auth_service

# Registers Bearer scheme in OpenAPI/Swagger UI
security_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description="Enter your signed JWT Bearer token obtained from POST /api/auth/login",
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(security_scheme),
) -> dict[str, Any]:
    """Dependency that extracts and validates the Bearer token, returning the user record."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except TokenRevokedError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked (logged out). Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except TokenValidationError as ve:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(ve)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_service = get_auth_service()
    username = payload.get("username")
    sub = payload.get("sub")

    user = None
    if sub and str(sub).isdigit():
        user = auth_service.get_user_by_id(int(sub))
    if not user and username:
        user = auth_service.get_user_by_username(username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("is_active", 1):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account has been deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Attach raw token to user dictionary for logout operations
    user["_token"] = token
    return user


def require_admin(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Enforces that the authenticated user possesses the 'ADMIN' role."""
    if current_user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: ADMIN role required to access this resource.",
        )
    return current_user


def require_analyst_or_admin(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Enforces that the user is either a verified ANALYST or an ADMIN."""
    if current_user.get("role") not in ["ADMIN", "ANALYST"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Insufficient privileges. Must be an ANALYST or ADMIN.",
        )
    return current_user
