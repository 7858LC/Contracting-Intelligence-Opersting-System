"""End-to-end proof for the team invite flow.

Before this fix there were two separate breaks in the same feature:

1. POST /tenants/members/invite queued send_invite_email, which logged and
   returned {"status": "sent"} without ever calling SendGrid — even with a
   key configured, no email went out, and the caller had no way to tell.
2. There was no way to redeem a TenantInvite token at all: no accept-invite
   endpoint, no frontend page. Even with a link in hand, an invited
   teammate could not actually join.

This covers both: the invite response always carries a usable link
regardless of email delivery, and POST /auth/accept-invite turns a valid
token into a real, logged-in TenantMember.
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
from cios.models.tenant import TenantInvite, TenantMember


def _fake_client_ip() -> str:
    return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


async def _register_owner(client: AsyncClient) -> dict:
    suffix = uuid.uuid4().hex[:10]
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"owner-{suffix}@example.com",
            "password": "InviteTest123!",
            "full_name": "Owner Test",
            "company_name": f"Invite Co {suffix}",
        },
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.anyio
async def test_invite_response_always_includes_a_usable_link(client: AsyncClient):
    owner = await _register_owner(client)
    headers = {"Authorization": f"Bearer {owner['access_token']}"}

    with patch(
        "cios.tasks.email.send_invite_email.delay",
        new=lambda *a, **kw: None,
    ):
        resp = await client.post(
            "/api/v1/tenants/members/invite",
            headers=headers,
            json={"email": "colleague@example.com", "role": "member"},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["email"] == "colleague@example.com"
    assert "invite_url" in body and "/auth/accept-invite?token=" in body["invite_url"]


@pytest.mark.anyio
async def test_accept_invite_creates_a_real_logged_in_member(client: AsyncClient):
    owner = await _register_owner(client)
    headers = {"Authorization": f"Bearer {owner['access_token']}"}

    invite_resp = await client.post(
        "/api/v1/tenants/members/invite",
        headers=headers,
        json={"email": "colleague@example.com", "role": "member"},
    )
    assert invite_resp.status_code == 200, invite_resp.text
    invite_url = invite_resp.json()["invite_url"]
    token = invite_url.split("token=")[1]

    accept_resp = await client.post(
        "/api/v1/auth/accept-invite",
        json={"token": token, "full_name": "Colleague Test", "password": "ColleagueTest123!"},
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert accept_resp.status_code == 201, accept_resp.text
    body = accept_resp.json()
    assert body["tenant_id"] == owner["tenant_id"]
    assert body["role"] == "member"
    assert body["access_token"]

    # The new member can immediately use the access token.
    me_resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "colleague@example.com"

    async with async_session_factory() as db:
        from sqlalchemy import text

        await db.execute(
            text("SELECT set_config('app.current_tenant', :t, false)"),
            {"t": owner["tenant_id"]},
        )
        member = (
            await db.execute(
                select(TenantMember).where(
                    TenantMember.email == "colleague@example.com",
                    TenantMember.tenant_id == uuid.UUID(owner["tenant_id"]),
                )
            )
        ).scalar_one()
        assert member.password_hash is not None
        assert member.role == "member"

        invite = (
            await db.execute(
                select(TenantInvite).where(TenantInvite.token == token)
            )
        ).scalar_one()
        assert invite.accepted_at is not None


@pytest.mark.anyio
async def test_accept_invite_rejects_unknown_token(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/accept-invite",
        json={"token": "not-a-real-token", "full_name": "Nobody", "password": "SomePassword123!"},
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_accept_invite_rejects_already_accepted_token(client: AsyncClient):
    owner = await _register_owner(client)
    headers = {"Authorization": f"Bearer {owner['access_token']}"}

    invite_resp = await client.post(
        "/api/v1/tenants/members/invite",
        headers=headers,
        json={"email": "twice@example.com", "role": "member"},
    )
    token = invite_resp.json()["invite_url"].split("token=")[1]

    first = await client.post(
        "/api/v1/auth/accept-invite",
        json={"token": token, "full_name": "First Accept", "password": "FirstAccept123!"},
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert first.status_code == 201, first.text

    second = await client.post(
        "/api/v1/auth/accept-invite",
        json={"token": token, "full_name": "Second Accept", "password": "SecondAccept123!"},
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert second.status_code == 409


@pytest.mark.anyio
async def test_accept_invite_rejects_expired_token(client: AsyncClient):
    owner = await _register_owner(client)

    async with async_session_factory() as db:
        from sqlalchemy import text

        await db.execute(
            text("SELECT set_config('app.current_tenant', :t, false)"),
            {"t": owner["tenant_id"]},
        )
        invite = TenantInvite(
            tenant_id=uuid.UUID(owner["tenant_id"]),
            email="expired@example.com",
            role="member",
            token="expired-token-" + uuid.uuid4().hex,
            expires_at=datetime.now(UTC) - timedelta(days=1),
            invited_by=uuid.UUID(owner["user_id"]),
        )
        db.add(invite)
        await db.commit()
        token = invite.token

    resp = await client.post(
        "/api/v1/auth/accept-invite",
        json={"token": token, "full_name": "Too Late", "password": "TooLatePassword123!"},
        headers={"X-Forwarded-For": _fake_client_ip()},
    )
    assert resp.status_code == 410


@pytest.mark.anyio
async def test_send_invite_email_calls_sendgrid_when_configured(monkeypatch):
    from cios.tasks.email import _send_via_sendgrid

    monkeypatch.setattr("cios.config.settings.sendgrid_api_key", "test-key")

    mock_post = AsyncMock()
    mock_post.return_value.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.post", mock_post):
        await _send_via_sendgrid("someone@example.com", "Subject", "<p>Body</p>")

    mock_post.assert_awaited_once()
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["json"]["personalizations"][0]["to"][0]["email"] == "someone@example.com"


@pytest.mark.anyio
async def test_send_invite_email_skips_cleanly_without_sendgrid_key(monkeypatch):
    from cios.tasks.email import send_invite_email

    monkeypatch.setattr("cios.config.settings.sendgrid_api_key", "")

    # send_invite_email is bind=True — calling it directly (not via .delay())
    # still runs synchronously with `self` bound to the task instance.
    result = send_invite_email("tenant-id", "someone@example.com", "tok")
    assert result == {"status": "skipped", "email": "someone@example.com"}
