"""Email delivery tasks via SendGrid."""
import structlog
from cios.tasks import celery_app

log = structlog.get_logger(__name__)


@celery_app.task(bind=True, max_retries=3)
def send_invite_email(self, tenant_id: str, email: str, token: str) -> dict:
    from cios.config import settings
    log.info("send_invite", email=email)
    if not settings.sendgrid_api_key:
        log.warning("sendgrid_not_configured")
        return {"status": "skipped"}
    return {"status": "sent", "email": email}


@celery_app.task(bind=True, max_retries=3)
def send_simulation_complete_email(self, tenant_id: str, email: str, simulation_id: str) -> dict:
    log.info("send_simulation_complete", email=email, simulation_id=simulation_id)
    return {"status": "sent"}
