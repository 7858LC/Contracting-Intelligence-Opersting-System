"""Security utilities — JWT, encryption, tenant key management."""
import base64
import hashlib
import hmac
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from cios.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── JWT ──────────────────────────────────────────────────────────────────────

def create_access_token(payload: dict[str, Any]) -> str:
    data = payload.copy()
    data["exp"] = datetime.now(UTC) + timedelta(minutes=settings.jwt_expiry_minutes)
    data["iat"] = datetime.now(UTC)
    data["type"] = "access"
    return jwt.encode(data, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(payload: dict[str, Any]) -> str:
    data = payload.copy()
    data["exp"] = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_expiry_days)
    data["iat"] = datetime.now(UTC)
    data["type"] = "refresh"
    return jwt.encode(data, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e


# ── Password ─────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── Tenant-Specific Encryption ────────────────────────────────────────────────

def derive_tenant_key(tenant_id: str, master_key: str | None = None) -> bytes:
    """Derive a per-tenant Fernet key from the master key + tenant salt."""
    mk = (master_key or settings.encryption_key).encode()
    salt = f"{settings.tenant_key_derivation_salt}:{tenant_id}".encode()
    derived = hashlib.pbkdf2_hmac("sha256", mk, salt, iterations=100_000)
    return base64.urlsafe_b64encode(derived)


class TenantEncryption:
    """Per-tenant field-level encryption."""

    def __init__(self, tenant_id: str, tenant_master_key: str | None = None) -> None:
        key = derive_tenant_key(tenant_id, tenant_master_key)
        self._fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode()).decode()

    def encrypt_bytes(self, data: bytes) -> bytes:
        return self._fernet.encrypt(data)

    def decrypt_bytes(self, data: bytes) -> bytes:
        return self._fernet.decrypt(data)


# ── API Key ───────────────────────────────────────────────────────────────────

def generate_api_key(prefix: str = "cios") -> tuple[str, str]:
    """Return (plaintext_key, hashed_key). Store only the hash."""
    raw = f"{prefix}_{os.urandom(32).hex()}"
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


def verify_api_key(plaintext: str, stored_hash: str) -> bool:
    computed = hashlib.sha256(plaintext.encode()).hexdigest()
    return hmac.compare_digest(computed, stored_hash)
