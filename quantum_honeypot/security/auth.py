"""Security, Cryptographic Password Hashing, and Token Authentication."""

import os
import hmac
import base64
import json
import time
import secrets
import hashlib
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..db.models import User

# Configuration
DEFAULT_SECRET_KEY = "quantumguard-enterprise-super-secret-key-32chars!!"
# If in production and no JWT_SECRET_KEY provided, generate a cryptographically strong 64-character secret
_AUTO_GENERATED_SECRET: Optional[str] = None
if not os.environ.get("JWT_SECRET_KEY"):
    _AUTO_GENERATED_SECRET = secrets.token_urlsafe(48)

SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or _AUTO_GENERATED_SECRET or DEFAULT_SECRET_KEY
TOKEN_EXPIRY_SECONDS = int(os.environ.get("TOKEN_EXPIRY_SECONDS", 86400)) # 24 hours
PBKDF2_ITERATIONS = 600000

security_scheme = HTTPBearer(auto_error=False)


def validate_security_configuration() -> None:
    """Validate JWT configuration."""
    global _AUTO_GENERATED_SECRET, SECRET_KEY
    if TOKEN_EXPIRY_SECONDS < 1:
        raise RuntimeError("TOKEN_EXPIRY_SECONDS must be a positive integer.")
    
    secret = os.environ.get("JWT_SECRET_KEY", "")
    is_prod = os.environ.get("ENVIRONMENT", "development").lower() == "production"
    
    # PaaS environments like Render, Heroku, or Cloud Run set specific environment variables
    is_render_or_paas = bool(
        os.environ.get("RENDER") 
        or os.environ.get("RENDER_SERVICE_ID") 
        or os.environ.get("IS_RENDER")
        or os.environ.get("VERCEL")
        or os.environ.get("AUTO_GENERATE_JWT_SECRET")
    )

    if is_prod:
        # Explicit insecure or default secret is always forbidden in production
        if secret and (len(secret.encode("utf-8")) < 32 or secret == DEFAULT_SECRET_KEY):
            raise RuntimeError(
                "Production requires JWT_SECRET_KEY with at least 32 bytes of unique random material."
            )
        # If no JWT_SECRET_KEY is provided in production, auto-generate a secure random 64-character key
        if not secret:
            if not _AUTO_GENERATED_SECRET:
                _AUTO_GENERATED_SECRET = secrets.token_urlsafe(48)
            os.environ["JWT_SECRET_KEY"] = _AUTO_GENERATED_SECRET
            SECRET_KEY = _AUTO_GENERATED_SECRET
            return


def get_secret_key() -> str:
    """Return the configured JWT secret, honoring runtime environment overrides."""
    return os.environ.get("JWT_SECRET_KEY") or SECRET_KEY or _AUTO_GENERATED_SECRET or DEFAULT_SECRET_KEY


def get_token_expiry_seconds(expires_delta: Optional[int] = None) -> int:
    """Resolve the expiry interval without treating zero as 'use default' value."""
    if expires_delta is None:
        return TOKEN_EXPIRY_SECONDS
    return int(expires_delta)

def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 with 600,000 iterations and 16-byte salt."""
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    salt_hex = salt.hex()
    key_hex = key.hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt_hex}${key_hex}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against the stored PBKDF2 hash using constant-time comparison."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        stored_key = bytes.fromhex(parts[3])
        if not 1 <= iterations <= 2_000_000 or len(salt) < 16 or len(stored_key) != 32:
            return False
        new_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
        return secrets.compare_digest(new_key, stored_key)
    except Exception:
        return False

def create_access_token(data: Dict[str, Any], expires_delta: Optional[int] = None) -> str:
    """Create a tamper-proof cryptographically signed token (HMAC-SHA256)."""
    to_encode = data.copy()
    expiry_seconds = get_token_expiry_seconds(expires_delta)
    expire = int(time.time()) + expiry_seconds
    to_encode.update({"exp": expire, "iat": int(time.time()), "iss": "quantumguard-soc"})
    
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(to_encode).encode()).decode().rstrip("=")
    
    signature_base = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(get_secret_key().encode(), signature_base, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    
    return f"{header_b64}.{payload_b64}.{sig_b64}"

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify token signature and expiration timestamp."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        
        # Verify signature
        signature_base = f"{header_b64}.{payload_b64}".encode()
        expected_sig = hmac.new(get_secret_key().encode(), signature_base, hashlib.sha256).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")
        
        if not secrets.compare_digest(sig_b64, expected_sig_b64):
            return None
            
        # Decode payload
        rem = len(payload_b64) % 4
        padded = payload_b64 + ("=" * (4 - rem) if rem else "")
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        
        if not isinstance(payload, dict) or payload.get("iss") != "quantumguard-soc" or "exp" not in payload:
            return None
        # Tokens are invalid at or after their expiry instant.
        try:
            if isinstance(payload["exp"], bool):
                return None
            exp_ts = int(payload["exp"])
        except (TypeError, ValueError):
            return None
        if int(time.time()) >= exp_ts:
            return None
            
        return payload
    except Exception:
        return None

def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Dependency: Extract current authenticated user from Bearer token."""
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    payload = decode_access_token(auth.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    user = db.query(User).filter(User.username == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account inactive or not found",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user

def require_role(allowed_roles: list[str]):
    """Role-based authorization dependency."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of permissions: {allowed_roles}"
            )
        return current_user
    return role_checker

require_admin = require_role(["admin"])
require_analyst = require_role(["admin", "analyst"])
require_viewer = require_role(["admin", "analyst", "viewer"])
