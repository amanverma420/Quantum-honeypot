"""Unit tests for PBKDF2 hashing, JWT tokens, and RBAC authorization."""

import pytest
from quantum_honeypot.security.auth import (
    hash_password, verify_password, create_access_token, decode_access_token,
    validate_security_configuration,
)

def test_password_hashing_and_verification():
    raw_pass = "QuantumGuard#Security2026!"
    hashed = hash_password(raw_pass)
    assert hashed.startswith("pbkdf2_sha256$600000$")
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword123", hashed) is False

def test_jwt_token_creation_and_tampering():
    payload = {"sub": "analyst1", "role": "analyst"}
    token = create_access_token(payload, expires_delta=3600)
    
    # Valid token verification
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "analyst1"
    assert decoded["role"] == "analyst"

    # Tampered token verification
    parts = token.split(".")
    tampered = f"{parts[0]}.{parts[1]}.tampered_signature"
    assert decode_access_token(tampered) is None

def test_expired_token():
    payload = {"sub": "analyst1", "role": "analyst"}
    # Expired 10 seconds ago
    token = create_access_token(payload, expires_delta=-10)
    assert decode_access_token(token) is None


def test_zero_expiry_token_is_rejected_immediately():
    payload = {"sub": "viewer1", "role": "viewer"}
    token = create_access_token(payload, expires_delta=0)
    assert decode_access_token(token) is None


def test_jwt_secret_override_is_used_at_runtime(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "a-runtime-secret-value-long-enough-for-testing")
    token = create_access_token({"sub": "analyst1", "role": "analyst"}, expires_delta=60)
    assert decode_access_token(token)["sub"] == "analyst1"
    monkeypatch.setenv("JWT_SECRET_KEY", "a-different-runtime-secret-value")
    assert decode_access_token(token) is None


def test_production_configuration_rejects_default_jwt_secret(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "quantumguard-enterprise-super-secret-key-32chars!!")
    with pytest.raises(RuntimeError, match="Production requires JWT_SECRET_KEY"):
        validate_security_configuration()

    monkeypatch.setenv("JWT_SECRET_KEY", "too-short")
    with pytest.raises(RuntimeError, match="Production requires JWT_SECRET_KEY"):
        validate_security_configuration()

    monkeypatch.setenv("JWT_SECRET_KEY", "a" * 64)
    validate_security_configuration()
