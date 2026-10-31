"""FraudShield AI - Authentication & Role-Based Access Schemas.

Pydantic models for user login, token issuance, credential management,
and role-based permissions (ADMIN and ANALYST).
"""

from typing import Literal
from pydantic import BaseModel, Field, EmailStr

UserRole = Literal["ADMIN", "ANALYST"]


class LoginRequest(BaseModel):
    """Credentials required to authenticate and obtain an access token."""
    username: str = Field(..., examples=["admin"], description="Username or registered email address")
    password: str = Field(..., examples=["Admin@FraudShield2026!"], description="Plaintext account password")


class AppUserResponse(BaseModel):
    """Public representation of an application security user."""
    id: int
    username: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    last_login: str | None = None
    created_at: str


class TokenResponse(BaseModel):
    """JWT bearer token and authenticated user profile payload."""
    access_token: str = Field(..., description="Signed RFC 7519 JSON Web Token")
    token_type: str = Field(default="bearer", description="Token schema type")
    expires_in: int = Field(..., description="Token validity window in seconds")
    user: AppUserResponse


class AppUserCreate(BaseModel):
    """Schema for administrator creating a new SOC analyst or admin."""
    username: str = Field(..., min_length=3, max_length=50, examples=["analyst_priya"])
    email: str = Field(..., examples=["priya@fraudshield.ai"])
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    full_name: str = Field(..., examples=["Priya Sharma"])
    role: UserRole = Field(default="ANALYST", description="Role permissions (ADMIN or ANALYST)")


class AppUserUpdate(BaseModel):
    """Schema for updating an existing application user."""
    email: str | None = None
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8)


class LogoutResponse(BaseModel):
    """Acknowledgement of token revocation on logout."""
    status: str = "success"
    message: str = "Successfully logged out. Token has been revoked."
