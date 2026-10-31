"""FraudShield AI - Authentication API Routes.

Handles user login, credential verification, JWT token issuance, session inspection,
and secure token revocation on logout.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from backend.schemas.auth import (
    LoginRequest,
    TokenResponse,
    AppUserResponse,
    AppUserUpdate,
    LogoutResponse,
)
from backend.services.auth_service import get_auth_service, AuthenticationError
from backend.api.deps import get_current_user

router = APIRouter(tags=["Authentication & Access Control"])


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login (Issue JWT)",
    description="Authenticates credentials (ADMIN or ANALYST) and issues a signed RFC 7519 JWT Bearer token.",
)
def login(credentials: LoginRequest) -> TokenResponse:
    """Authenticates username/password and returns a bearer token."""
    service = get_auth_service()
    try:
        result = service.login(credentials.username, credentials.password)
        user_data = result["user"]
        user_model = AppUserResponse(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            full_name=user_data["full_name"],
            role=user_data["role"],
            is_active=bool(user_data["is_active"]),
            last_login=user_data.get("last_login"),
            created_at=user_data["created_at"],
        )
        return TokenResponse(
            access_token=result["access_token"],
            token_type=result["token_type"],
            expires_in=result["expires_in"],
            user=user_model,
        )
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post(
    "/auth/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="User Logout (Revoke Token)",
    description="Revokes the active JWT Bearer token and terminates the session.",
)
def logout(current_user: dict = Depends(get_current_user)) -> LogoutResponse:
    """Revokes the current user's session token."""
    service = get_auth_service()
    token = current_user.get("_token", "")
    if token:
        service.logout(token)
    return LogoutResponse(status="success", message="Successfully logged out. Token has been revoked.")


@router.get(
    "/auth/me",
    response_model=AppUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current User Profile",
    description="Returns the profile and role details of the currently authenticated user.",
)
def get_me(current_user: dict = Depends(get_current_user)) -> AppUserResponse:
    """Returns the authenticated user's claims and active permissions."""
    return AppUserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        is_active=bool(current_user["is_active"]),
        last_login=current_user.get("last_login"),
        created_at=current_user["created_at"],
    )


@router.patch(
    "/auth/me",
    response_model=AppUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Current User Profile",
    description="Updates email, full name, or password of the currently authenticated user.",
)
def update_me(
    payload: AppUserUpdate,
    current_user: dict = Depends(get_current_user),
) -> AppUserResponse:
    """Updates profile details for the authenticated user session."""
    service = get_auth_service()
    updates = {k: v for k, v in payload.model_dump().items() if v is not None and k != "role"}
    updated = service.update_app_user(current_user["id"], updates)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User record not found.",
        )
    return AppUserResponse(
        id=updated["id"],
        username=updated["username"],
        email=updated["email"],
        full_name=updated["full_name"],
        role=updated["role"],
        is_active=bool(updated["is_active"]),
        last_login=updated.get("last_login"),
        created_at=updated["created_at"],
    )
