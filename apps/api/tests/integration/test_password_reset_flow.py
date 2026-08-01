"""End-to-end proof for the password reset flow.

There was no password-reset flow anywhere in the product before this — no
endpoint, no frontend page, not even an admin-side way to reset a tenant
member's password. A user who forgot or mistyped their password had no
self-serve way back into their account; POST /auth/login's "Invalid
credentials" only ever means a genuine email/password mismatch (see
auth.py's login()), so there was nothing else to try.

Covers the full loop: POST /auth/forgot-password always returns the same
generic response regardless of whether the email matches an account (never
reveals the token/link itself, unlike the admin-authenticated invite flow),
and POST /auth/reset-password turns a valid token into an actually-changed
password that the old one no longer works for.
"""

from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from cios.core.database import async_session_factory
from cios.models.tenant import PasswordResetToken, TenantMember


def _fake_client_ip() -> str:
    return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


async def _issued_token_for(tenant_id: str, email: str) -> str:
    async with async_session_factory() as db:
        from sqlalchemy import text

        await db.execute(
            text("SELECT set_config('app.current_tenant', :t, false)"),
            {"t": tenant_id},
        )
        member = (
            await db.execute(
                select(TenantMember).where(
                    TenantMember.tenant_id == uuid.UUID(tenant_id),
                    TenantMember.email == email,
                )
            )
        ).scalar_one()
        reset_token = (
            await db.execute(
                select(PasswordResetToken)
                .where(PasswordResetToken.tenant_member_id == member.id)
                .order_by(PasswordResetToken.created_at.desc())
            )
        ).scalars().first()
        assert reset_token is not None
        return reset_token.token


@pytest.mark.anyio
async def test_forgot_password_and_reset_round_trip(client: AsyncClient):
    suffix = uuid.uuid4().hex[:10]
    email = f"roundtrip-{suffix}@example.com"
    register_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "OriginalPass123!",
            "full_name": "Roundtrip Test",
            "company_name": f"Roundtrip Co {suffix}",
        },
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert register_resp.status_code == 201, register_resp.text
    tenant_id = register_resp.json()["tenant_id"]

    with patch("cios.tasks.email.send_password_reset_email.delay", new=lambda *a, **kw: None):
        forgot_resp = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": email},
            headers={"X-Forwarded-For": _fake_client_ip()},
        )
    assert forgot_resp.status_code == 200, forgot_resp.text
    assert forgot_resp.json() == {"status": "ok"}

    token = await _issued_token_for(tenant_id, email)

    reset_resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "BrandNewPass456!"},
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert reset_resp.status_code == 200, reset_resp.text
    assert reset_resp.json() == {"status": "ok"}

    # Old password no longer works.
    old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "OriginalPass123!"},
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert old_login.status_code == 401

    # New password does.
    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "BrandNewPass456!"},
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert new_login.status_code == 200, new_login.text


@pytest.mark.anyio
async def test_forgot_password_returns_same_response_for_unknown_email(client: AsyncClient):
    # Never reveal whether an email is registered — same generic response
    # for a real account (covered above) and a nonexistent one.
    resp = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": f"nobody-{uuid.uuid4().hex[:10]}@example.com"},
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_reset_password_rejects_unknown_token(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "not-a-real-token", "new_password": "SomePassword123!"},
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_reset_password_rejects_reused_token(client: AsyncClient):
    suffix = uuid.uuid4().hex[:10]
    email = f"reused-{suffix}@example.com"
    register_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "OriginalPass123!",
            "full_name": "Reused Test",
            "company_name": f"Reused Co {suffix}",
        },
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    tenant_id = register_resp.json()["tenant_id"]

    with patch("cios.tasks.email.send_password_reset_email.delay", new=lambda *a, **kw: None):
        await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": email},
            headers={"X-Forwarded-For": _fake_client_ip()},
        )
    token = await _issued_token_for(tenant_id, email)

    first = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "FirstReset123!"},
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert first.status_code == 200, first.text

    second = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "SecondReset123!"},
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert second.status_code == 409


@pytest.mark.anyio
async def test_reset_password_rejects_expired_token(client: AsyncClient):
    suffix = uuid.uuid4().hex[:10]
    email = f"expired-{suffix}@example.com"
    register_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "OriginalPass123!",
            "full_name": "Expired Test",
            "company_name": f"Expired Co {suffix}",
        },
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    tenant_id = register_resp.json()["tenant_id"]

    async with async_session_factory() as db:
        from sqlalchemy import text

        await db.execute(
            text("SELECT set_config('app.current_tenant', :t, false)"),
            {"t": tenant_id},
        )
        member = (
            await db.execute(
                select(TenantMember).where(
                    TenantMember.tenant_id == uuid.UUID(tenant_id),
                    TenantMember.email == email,
                )
            )
        ).scalar_one()
        reset_token = PasswordResetToken(
            tenant_member_id=member.id,
            token="expired-reset-" + uuid.uuid4().hex,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        db.add(reset_token)
        await db.commit()
        token = reset_token.token

    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "TooLatePassword123!"},
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert resp.status_code == 410


@pytest.mark.anyio
async def test_send_password_reset_email_skips_cleanly_without_sendgrid_key(monkeypatch):
    from cios.tasks.email import send_password_reset_email

    monkeypatch.setattr("cios.config.settings.sendgrid_api_key", "")

    # bind=True — calling directly (not via .delay()) still runs synchronously
    # with `self` bound to the task instance.
    result = send_password_reset_email("someone@example.com", "tok")
    assert result == {"status": "skipped", "email": "someone@example.com"}


@pytest.mark.anyio
async def test_send_password_reset_email_calls_sendgrid_when_configured(monkeypatch):
    from cios.tasks.email import _send_via_sendgrid

    monkeypatch.setattr("cios.config.settings.sendgrid_api_key", "test-key")

    mock_post = AsyncMock()
    mock_post.return_value.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.post", mock_post):
        await _send_via_sendgrid("someone@example.com", "Subject", "<p>Body</p>")

    mock_post.assert_awaited_once()
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["json"]["personalizations"][0]["to"][0]["email"] == "someone@example.com"
