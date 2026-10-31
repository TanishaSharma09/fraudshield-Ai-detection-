"""FraudShield AI - Authentication & User Management Service.

Coordinates credentials validation, password hashing, JWT token issuance,
role checking, and token revocation for SOC analysts and system administrators.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Literal
from backend.core.config import settings
from backend.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    revoke_token,
)
from database.connection import execute_stmt, query_all, query_one


class AuthenticationError(Exception):
    """Raised when authentication credentials fail validation."""
    pass


class UserExistsError(Exception):
    """Raised when an attempt is made to create a duplicate username or email."""
    pass


class AuthService:
    """Service handling application user authentication, tokens, and role administration."""

    def authenticate_user(self, username_or_email: str, plain_password: str) -> dict[str, Any] | None:
        """Verifies credentials against app_users and updates last_login timestamp."""
        clean_ident = username_or_email.strip().lower()

        row = query_one(
            """
            SELECT * FROM app_users 
            WHERE LOWER(username) = ? OR LOWER(email) = ?;
            """,
            (clean_ident, clean_ident),
        )

        if not row:
            return None

        user = dict(row)
        if not user.get("is_active", 1):
            return None

        if not verify_password(plain_password, user["hashed_password"]):
            return None

        # Update last login timestamp
        now_utc = datetime.now(timezone.utc).isoformat()
        execute_stmt("UPDATE app_users SET last_login = ? WHERE id = ?;", (now_utc, user["id"]))
        user["last_login"] = now_utc
        user.pop("hashed_password", None)
        return user

    def login(self, username_or_email: str, plain_password: str) -> dict[str, Any]:
        """Authenticates user and returns standard token payload."""
        user = self.authenticate_user(username_or_email, plain_password)
        if not user:
            raise AuthenticationError("Invalid username or password.")

        # Generate JWT Bearer Token
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        token_claims = {
            "sub": str(user["id"]),
            "username": user["username"],
            "role": user["role"],
            "email": user["email"],
        }
        access_token = create_access_token(data=token_claims, expires_delta=expires_delta)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": int(expires_delta.total_seconds()),
            "user": user,
        }

    def logout(self, token: str) -> bool:
        """Revokes token by adding its unique jti to blacklist."""
        try:
            payload = decode_access_token(token, verify_expiration=False)
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti:
                exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc).isoformat() if exp else None
                revoke_token(jti, expires_at=exp_dt)
                return True
        except Exception:
            pass
        return True

    def create_app_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: str,
        role: Literal["ADMIN", "ANALYST"] = "ANALYST",
    ) -> dict[str, Any]:
        """Creates a new application user (Admin privilege required)."""
        clean_user = username.strip().lower()
        clean_email = email.strip().lower()

        # Check collisions
        existing = query_one(
            "SELECT id FROM app_users WHERE LOWER(username) = ? OR LOWER(email) = ?;",
            (clean_user, clean_email),
        )
        if existing:
            raise UserExistsError(f"User with username '{clean_user}' or email '{clean_email}' already exists.")

        hashed_pwd = hash_password(password)
        now_utc = datetime.now(timezone.utc).isoformat()

        user_id = execute_stmt(
            """
            INSERT INTO app_users 
            (username, email, full_name, hashed_password, role, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?);
            """,
            (clean_user, clean_email, full_name.strip(), hashed_pwd, role.upper(), now_utc, now_utc),
        )

        created = self.get_user_by_id(user_id)
        return created  # type: ignore

    def get_user_by_id(self, user_id: int) -> dict[str, Any] | None:
        """Retrieves user details without exposing password hash."""
        row = query_one(
            "SELECT id, username, email, full_name, role, is_active, last_login, created_at FROM app_users WHERE id = ?;",
            (user_id,),
        )
        return dict(row) if row else None

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        """Retrieves user details by username."""
        row = query_one(
            "SELECT id, username, email, full_name, role, is_active, last_login, created_at FROM app_users WHERE LOWER(username) = ?;",
            (username.strip().lower(),),
        )
        return dict(row) if row else None

    def list_app_users(self, limit: int = 50, offset: int = 0) -> tuple[list[dict[str, Any]], int]:
        """Lists application accounts for administrator management."""
        cnt = query_one("SELECT COUNT(*) AS total FROM app_users;")
        total = cnt["total"] if cnt else 0

        rows = query_all(
            """
            SELECT id, username, email, full_name, role, is_active, last_login, created_at 
            FROM app_users 
            ORDER BY id ASC 
            LIMIT ? OFFSET ?;
            """,
            (limit, offset),
        )
        return [dict(r) for r in rows], total

    def update_app_user(self, user_id: int, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Updates user role, status, email, or password."""
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        now_utc = datetime.now(timezone.utc).isoformat()
        pwd_hash = hash_password(updates["password"]) if updates.get("password") else None

        execute_stmt(
            """
            UPDATE app_users SET
                email = COALESCE(?, email),
                full_name = COALESCE(?, full_name),
                role = COALESCE(?, role),
                is_active = COALESCE(?, is_active),
                hashed_password = COALESCE(?, hashed_password),
                updated_at = ?
            WHERE id = ?;
            """,
            (
                updates.get("email"),
                updates.get("full_name"),
                updates.get("role"),
                updates.get("is_active"),
                pwd_hash,
                now_utc,
                user_id,
            ),
        )
        return self.get_user_by_id(user_id)

    def delete_app_user(self, user_id: int) -> bool:
        """Deletes an application user."""
        count = execute_stmt("DELETE FROM app_users WHERE id = ?;", (user_id,))
        return count > 0


# Singleton instance helper
_auth_service: AuthService | None = None


def get_auth_service() -> AuthService:
    """Returns or initialises the singleton AuthService."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
