"""FraudShield AI - Cryptographic Security & Token Management Module.

Provides:
- OWASP/NIST-compliant password hashing via PBKDF2-HMAC-SHA256 with 100,000 rounds and per-user cryptographic salts.
- Constant-time verification to prevent timing attacks.
- RFC 7519 compliant JSON Web Token (JWT) generation and verification using HMAC-SHA256 (HS256).
- Token revocation and blacklisting for secure logout.
"""

import json
import base64
import hmac
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Any

from backend.core.config import settings
from database.connection import execute_stmt, query_one

# In-memory revocation cache for zero-latency lookups
_REVOKED_TOKENS_CACHE: set[str] = set()


class SecurityError(Exception):
    """Base exception for security and authentication errors."""
    pass


class TokenValidationError(SecurityError):
    """Raised when token signature or format is invalid."""
    pass


class TokenExpiredError(SecurityError):
    """Raised when token expiration timestamp has passed."""
    pass


class TokenRevokedError(SecurityError):
    """Raised when token has been revoked via logout."""
    pass


# ===========================================================================
# 1. Password Hashing & Verification (PBKDF2-HMAC-SHA256)
# ===========================================================================
def hash_password(password: str) -> str:
    """Hashes a plaintext password using PBKDF2-HMAC-SHA256 with a random 16-byte salt and 100,000 iterations.

    Format: pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
    """
    if not password:
        raise ValueError("Password cannot be empty.")

    salt = secrets.token_bytes(16)
    iterations = 100_000
    derived_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${derived_key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a stored PBKDF2-HMAC-SHA256 hash using constant-time comparison."""
    if not plain_password or not hashed_password:
        return False

    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False

        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_key = bytes.fromhex(parts[3])

        computed_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(computed_key, expected_key)
    except Exception:
        return False


# ===========================================================================
# 2. Base64URL Encoding & Decoding (RFC 7515 / RFC 7519)
# ===========================================================================
def _b64url_encode(data: bytes) -> str:
    """Encodes bytes to base64url string without trailing padding '='."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    """Decodes a base64url string, adding required padding '=' if necessary."""
    padding = "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode((s + padding).encode("ascii"))


# ===========================================================================
# 3. RFC 7519 JSON Web Token (JWT) Implementation
# ===========================================================================
def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
    secret_key: str | None = None,
) -> str:
    """Generates an RFC 7519 standard JSON Web Token (JWT) signed with HMAC-SHA256 (HS256).

    Args:
        data: Claims payload (must include 'sub', 'username', 'role').
        expires_delta: Custom expiration delta (defaults to config settings).
        secret_key: Optional override for secret key.

    Returns:
        Standard JWT string: <header>.<payload>.<signature>
    """
    key = (secret_key or settings.SECRET_KEY).encode("utf-8")
    now_utc = datetime.now(timezone.utc)
    delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire_utc = now_utc + delta

    # 1. Header
    header = {"alg": "HS256", "typ": "JWT"}
    header_json = json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    header_b64 = _b64url_encode(header_json)

    # 2. Payload
    payload = data.copy()
    payload["iat"] = int(now_utc.timestamp())
    payload["exp"] = int(expire_utc.timestamp())
    payload["jti"] = payload.get("jti") or secrets.token_hex(16)

    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = _b64url_encode(payload_json)

    # 3. Signature
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(key, signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(
    token: str,
    secret_key: str | None = None,
    verify_expiration: bool = True,
) -> dict[str, Any]:
    """Decodes, verifies the cryptographic signature, and checks revocation for a JWT string.

    Raises:
        TokenValidationError: If format is corrupted or signature verification fails.
        TokenExpiredError: If current time exceeds 'exp' claim.
        TokenRevokedError: If token has been revoked via logout.
    """
    if not token or not isinstance(token, str):
        raise TokenValidationError("Token string is missing or invalid.")

    parts = token.strip().split(".")
    if len(parts) != 3:
        raise TokenValidationError("Invalid token format: expected 3 dot-separated segments.")

    header_b64, payload_b64, sig_b64 = parts
    key = (secret_key or settings.SECRET_KEY).encode("utf-8")

    # 1. Verify signature
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = hmac.new(key, signing_input, hashlib.sha256).digest()

    try:
        actual_sig = _b64url_decode(sig_b64)
    except Exception as e:
        raise TokenValidationError(f"Invalid signature encoding: {e}")

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise TokenValidationError("Token signature verification failed.")

    # 2. Decode payload
    try:
        payload_bytes = _b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        raise TokenValidationError(f"Invalid payload encoding: {e}")

    # 3. Check revocation
    jti = payload.get("jti")
    if jti and is_token_revoked(jti):
        raise TokenRevokedError("Token has been revoked or session was logged out.")

    # 4. Check expiration
    if verify_expiration:
        exp = payload.get("exp")
        if not exp:
            raise TokenValidationError("Token missing expiration claim ('exp').")
        now_ts = int(datetime.now(timezone.utc).timestamp())
        if now_ts >= exp:
            raise TokenExpiredError("Token has expired.")

    return payload


# ===========================================================================
# 4. Token Blacklist / Revocation Management
# ===========================================================================
def revoke_token(jti: str, expires_at: str | None = None) -> None:
    """Revokes a JWT by recording its unique 'jti' in the blacklist."""
    clean_jti = jti.strip()
    _REVOKED_TOKENS_CACHE.add(clean_jti)

    exp_str = expires_at or (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    try:
        execute_stmt(
            """
            INSERT OR IGNORE INTO token_blacklist (token_jti, expires_at)
            VALUES (?, ?);
            """,
            (clean_jti, exp_str),
        )
    except Exception:
        # Table might not exist in early tests; cache handles memory revocation
        pass


def is_token_revoked(jti: str) -> bool:
    """Checks whether a token 'jti' is present in the revocation blacklist."""
    clean_jti = jti.strip()
    if clean_jti in _REVOKED_TOKENS_CACHE:
        return True

    try:
        row = query_one("SELECT token_jti FROM token_blacklist WHERE token_jti = ?;", (clean_jti,))
        if row:
            _REVOKED_TOKENS_CACHE.add(clean_jti)
            return True
    except Exception:
        pass

    return False
