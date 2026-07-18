"""Celery task workers for async processing."""
from celery import Celery
from cios.config import settings

celery_app = Celery(
    "cios",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "cios.tasks.analysis",
        "cios.tasks.simulation",
        "cios.tasks.ingestion",
        "cios.tasks.bid_analysis",
        "cios.tasks.gap_analysis",
        "cios.tasks.teaming",
        "cios.tasks.competitive_intel",
        "cios.tasks.scoring",
        "cios.tasks.billing",
        "cios.tasks.email",
        "cios.tasks.onboarding",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "cios.tasks.simulation.*": {"queue": "simulations"},
        "cios.tasks.ingestion.*": {"queue": "ingestion"},
        "cios.tasks.analysis.*": {"queue": "analysis"},
        "cios.tasks.email.*": {"queue": "email"},
    },
)
