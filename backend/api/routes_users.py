"""FraudShield AI - Application User Management Routes (ADMIN Only).

Allows system administrators to manage application accounts (SOC Analysts and Administrators),
change roles, deactivate accounts, and inspect audit activity.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from backend.schemas.auth import AppUserResponse, AppUserCreate, AppUserUpdate
from backend.services.auth_service import get_auth_service, UserExistsError
from backend.api.deps import require_admin

router = APIRouter(tags=["User Administration (ADMIN Only)"])


class AppUserListResponse(BaseModel):
    """Paginated list of application accounts."""
    total: int
    limit: int
    offset: int
    users: list[AppUserResponse]


@router.get(
    "/users",
    response_model=AppUserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Application Users (ADMIN Only)",
    description="Returns a paginated list of registered application users (SOC Analysts and Administrators). Requires ADMIN role.",
)
def list_users(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_admin: dict = Depends(require_admin),
) -> AppUserListResponse:
    """Lists users in the app_users table."""
    service = get_auth_service()
    rows, total = service.list_app_users(limit=limit, offset=offset)

    user_models = [
        AppUserResponse(
            id=r["id"],
            username=r["username"],
            email=r["email"],
            full_name=r["full_name"],
            role=r["role"],
            is_active=bool(r["is_active"]),
            last_login=r.get("last_login"),
            created_at=r["created_at"],
        )
        for r in rows
    ]

    return AppUserListResponse(total=total, limit=limit, offset=offset, users=user_models)


@router.post(
    "/users",
    response_model=AppUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Application User (ADMIN Only)",
    description="Registers a new SOC Analyst or Administrator account with role assignments. Requires ADMIN role.",
)
def create_user(
    payload: AppUserCreate,
    current_admin: dict = Depends(require_admin),
) -> AppUserResponse:
    """Creates a new application user."""
    service = get_auth_service()
    try:
        user = service.create_app_user(
            username=payload.username,
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            role=payload.role,
        )
        return AppUserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
            is_active=bool(user["is_active"]),
            last_login=user.get("last_login"),
            created_at=user["created_at"],
        )
    except UserExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get(
    "/users/{user_id}",
    response_model=AppUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get User by ID (ADMIN Only)",
    description="Retrieves specific application account details. Requires ADMIN role.",
)
def get_user(
    user_id: int,
    current_admin: dict = Depends(require_admin),
) -> AppUserResponse:
    """Retrieves single user by id."""
    service = get_auth_service()
    user = service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} was not found.",
        )
    return AppUserResponse(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        full_name=user["full_name"],
        role=user["role"],
        is_active=bool(user["is_active"]),
        last_login=user.get("last_login"),
        created_at=user["created_at"],
    )


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete User (ADMIN Only)",
    description="Permanently deletes an application account. Requires ADMIN role.",
)
def delete_user(
    user_id: int,
    current_admin: dict = Depends(require_admin),
) -> dict[str, str]:
    """Deletes an application user."""
    service = get_auth_service()
    user = service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} was not found.",
        )

    if user["username"] == current_admin["username"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot delete their own active account.",
        )

    service.delete_app_user(user_id)
    return {"status": "success", "message": f"User {user['username']} deleted successfully."}


@router.patch(
    "/users/{user_id}",
    response_model=AppUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update User (ADMIN Only)",
    description="Updates role, active status, full name, email, or password for an application user account. Requires ADMIN role.",
)
def update_user(
    user_id: int,
    payload: AppUserUpdate,
    current_admin: dict = Depends(require_admin),
) -> AppUserResponse:
    """Updates application user account fields."""
    service = get_auth_service()
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    updated = service.update_app_user(user_id, updates)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} was not found.",
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
