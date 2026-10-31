"""Unit tests for cryptographic security, password hashing, and JWT tokens."""

import time
from datetime import timedelta
import pytest
from backend.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    revoke_token,
    is_token_revoked,
    TokenValidationError,
    TokenExpiredError,
    TokenRevokedError,
)


def test_password_hashing_and_verification():
    """Verifies that PBKDF2-HMAC-SHA256 password hashing and verification work securely."""
    password = "SuperSecretPassword123!"

    # Hash password
    hashed = hash_password(password)
    assert hashed.startswith("pbkdf2_sha256$100000$")

    # Salting: hashing the same password twice yields different salts and hashes
    hashed2 = hash_password(password)
    assert hashed != hashed2

    # Verification
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password(password, "malformed_hash") is False


def test_password_empty_raises_error():
    """Verifies ValueError when hashing empty password."""
    with pytest.raises(ValueError):
        hash_password("")


def test_jwt_token_creation_and_decoding():
    """Verifies standard JWT creation, signature validation, and claims retrieval."""
    claims = {"sub": "1", "username": "admin", "role": "ADMIN"}
    token = create_access_token(claims, expires_delta=timedelta(minutes=30))

    assert isinstance(token, str)
    assert len(token.split(".")) == 3

    decoded = decode_access_token(token)
    assert decoded["sub"] == "1"
    assert decoded["username"] == "admin"
    assert decoded["role"] == "ADMIN"
    assert "exp" in decoded
    assert "iat" in decoded
    assert "jti" in decoded


def test_jwt_tampered_token_fails():
    """Verifies that tampering with header, payload, or signature is rejected."""
    claims = {"sub": "2", "username": "analyst", "role": "ANALYST"}
    token = create_access_token(claims)
    parts = token.split(".")

    # Tamper with signature
    tampered_sig = parts[0] + "." + parts[1] + ".invalidSignature123"
    with pytest.raises(TokenValidationError):
        decode_access_token(tampered_sig)

    # Tamper with payload (e.g. elevating role to ADMIN without valid signature)
    elevated_payload_b64 = "eyJzdWIiOiIyIiwidXNlcm5hbWUiOiJhbmFseXN0Iiwicm9sZSI6IkFETUlOIn0"
    tampered_token = parts[0] + "." + elevated_payload_b64 + "." + parts[2]
    with pytest.raises(TokenValidationError):
        decode_access_token(tampered_token)


def test_jwt_expired_token_fails():
    """Verifies that expired tokens raise TokenExpiredError."""
    claims = {"sub": "3", "username": "test_user", "role": "ANALYST"}
    # Token with negative expiration delta (already expired)
    expired_token = create_access_token(claims, expires_delta=timedelta(seconds=-10))

    with pytest.raises(TokenExpiredError):
        decode_access_token(expired_token)


def test_jwt_revoked_token_fails():
    """Verifies that revoking a token prevents future authentication."""
    import secrets
    unique_jti = f"REVOKE-TEST-{secrets.token_hex(8)}"
    claims = {"sub": "4", "username": "revoked_user", "role": "ANALYST", "jti": unique_jti}
    token = create_access_token(claims)

    # Valid before revocation
    decoded = decode_access_token(token)
    assert decoded["jti"] == unique_jti

    # Revoke token
    revoke_token(unique_jti)
    assert is_token_revoked(unique_jti) is True

    # Attempt decoding after revocation
    with pytest.raises(TokenRevokedError):
        decode_access_token(token)
