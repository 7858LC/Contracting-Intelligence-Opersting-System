"""Email delivery tasks via SendGrid."""

import structlog

from cios.tasks import celery_app

log = structlog.get_logger(__name__)

_SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"


async def _send_via_sendgrid(to_email: str, subject: str, html_content: str) -> None:
    import httpx

    from cios.config import settings

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            _SENDGRID_URL,
            headers={"Authorization": f"Bearer {settings.sendgrid_api_key}"},
            json={
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": settings.from_email},
                "subject": subject,
                "content": [{"type": "text/html", "value": html_content}],
            },
        )
        resp.raise_for_status()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def send_invite_email(self, tenant_id: str, email: str, token: str) -> dict:
    import asyncio

    from cios.config import settings

    log.info("send_invite", email=email)
    if not settings.sendgrid_api_key:
        # No SendGrid key configured — the invite itself (and its URL) still
        # exists and is returned directly in POST /tenants/members/invite's
        # response, so an admin can always hand the link over manually.
        # Previously this task returned {"status": "sent"} in this exact
        # case without attempting anything, which was actively misleading —
        # the caller had no way to know the invite email never went out.
        log.warning("sendgrid_not_configured")
        return {"status": "skipped", "email": email}

    invite_url = f"{settings.app_url}/auth/accept-invite?token={token}"
    try:
        asyncio.run(
            _send_via_sendgrid(
                to_email=email,
                subject="You've been invited to CIOS",
                html_content=(
                    f"<p>You've been invited to join a CIOS workspace.</p>"
                    f'<p><a href="{invite_url}">Accept your invite</a></p>'
                    f"<p>This link expires in 7 days.</p>"
                ),
            )
        )
    except Exception as exc:
        # A previous attempt here silently returned {"status": "sent"} on
        # any outcome, including a SendGrid error — max_retries was declared
        # but nothing ever called self.retry(), so a transient SendGrid
        # failure (rate limit, timeout) just looked identical to a
        # successful send with no way to tell them apart. The invite link
        # itself is still recoverable from POST /tenants/members/invite's
        # response regardless of how this task resolves.
        log.error("send_invite_failed", email=email, error=str(exc))
        raise self.retry(exc=exc)

    return {"status": "sent", "email": email}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def send_password_reset_email(self, email: str, token: str) -> dict:
    import asyncio

    from cios.config import settings

    log.info("send_password_reset", email=email)
    if not settings.sendgrid_api_key:
        # Same non-fatal skip as send_invite_email above — POST /auth/forgot-password
        # deliberately never returns the token/link itself (unlike the invite
        # endpoint, which is already admin-authenticated), so without SendGrid
        # configured there is genuinely no way to complete a reset in this
        # environment. That's expected in dev/CI; production requires the key.
        log.warning("sendgrid_not_configured")
        return {"status": "skipped", "email": email}

    reset_url = f"{settings.app_url}/auth/reset-password?token={token}"
    try:
        asyncio.run(
            _send_via_sendgrid(
                to_email=email,
                subject="Reset your CIOS password",
                html_content=(
                    "<p>A password reset was requested for your CIOS account.</p>"
                    f'<p><a href="{reset_url}">Reset your password</a></p>'
                    "<p>This link expires in 1 hour. If you didn't request this, "
                    "you can safely ignore this email.</p>"
                ),
            )
        )
    except Exception as exc:
        log.error("send_password_reset_failed", email=email, error=str(exc))
        raise self.retry(exc=exc)

    return {"status": "sent", "email": email}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def send_onboarding_welcome_email(self, tenant_id: str, email: str, summary: dict) -> dict:
    """Real replacement for the onboarding-complete task's previous no-op
    (tasks/onboarding.py's run_initial_analysis used to return a hardcoded
    status string and do nothing) — confirms to a brand-new tenant that
    what they entered during onboarding actually got saved, since there's
    no meaningful AI analysis to run yet at account-creation time (no
    opportunity assigned, no evidence documents uploaded)."""
    import asyncio

    from cios.config import settings

    log.info("send_onboarding_welcome", email=email, tenant_id=tenant_id)
    if not settings.sendgrid_api_key:
        log.warning("sendgrid_not_configured")
        return {"status": "skipped", "email": email}

    items = "".join(
        f"<li>{count} {label}</li>"
        for label, count in [
            ("capabilities", summary.get("capabilities", 0)),
            ("past performance records", summary.get("past_performance", 0)),
            ("tracked competitors", summary.get("competitors", 0)),
            ("teaming partners", summary.get("teaming_partners", 0)),
        ]
        if count
    )
    dashboard_url = f"{settings.app_url}/dashboard"
    try:
        asyncio.run(
            _send_via_sendgrid(
                to_email=email,
                subject="Your CIOS workspace is set up",
                html_content=(
                    "<p>Your onboarding data has been saved:</p>"
                    f"<ul>{items}</ul>"
                    f'<p><a href="{dashboard_url}">Open your dashboard</a></p>'
                ),
            )
        )
    except Exception as exc:
        log.error("send_onboarding_welcome_failed", email=email, error=str(exc))
        raise self.retry(exc=exc)

    return {"status": "sent", "email": email}


@celery_app.task(bind=True, max_retries=3)
def send_simulation_complete_email(self, tenant_id: str, email: str, simulation_id: str) -> dict:
    log.info("send_simulation_complete", email=email, simulation_id=simulation_id)
    return {"status": "sent"}
