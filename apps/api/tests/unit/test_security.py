"""Tests for security utilities."""

import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/test")
os.environ.setdefault("JWT_SECRET", "test_secret_minimum_32_characters_long")
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)
os.environ.setdefault("ANTHROPIC_API_KEY", "test_key")

from cios.core.security import (
    TenantEncryption,
    create_access_token,
    decode_token,
    generate_api_key,
    hash_password,
    verify_api_key,
    verify_password,
)


def test_password_round_trip():
    plain = "SecurePassword123!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)
    assert not verify_password("WrongPassword", hashed)


def test_jwt_round_trip():
    payload = {
        "sub": "user-123",
        "tenant_id": "tenant-456",
        "email": "test@example.com",
        "role": "admin",
        "plan": "pro",
    }
    token = create_access_token(payload)
    decoded = decode_token(token)
    assert decoded["sub"] == "user-123"
    assert decoded["tenant_id"] == "tenant-456"
    assert decoded["type"] == "access"


def test_jwt_invalid_token_raises():
    with pytest.raises(ValueError):
        decode_token("not.a.valid.token")


def test_api_key_generation_and_verification():
    plaintext, hashed = generate_api_key("cios")
    assert plaintext.startswith("cios_")
    assert len(hashed) == 64
    assert verify_api_key(plaintext, hashed)
    assert not verify_api_key("wrong_key", hashed)


def test_tenant_encryption_round_trip():
    enc = TenantEncryption("tenant-123")
    original = "Sensitive procurement data"
    encrypted = enc.encrypt(original)
    assert encrypted != original
    decrypted = enc.decrypt(encrypted)
    assert decrypted == original


def test_different_tenants_different_keys():
    enc1 = TenantEncryption("tenant-001")
    enc2 = TenantEncryption("tenant-002")
    data = "secret data"
    encrypted = enc1.encrypt(data)
    with pytest.raises(Exception):
        enc2.decrypt(encrypted)
