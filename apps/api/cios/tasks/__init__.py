"""Celery task workers for async processing."""

from celery import Celery
from celery.schedules import crontab

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
        "cios.tasks.pir",
        "cios.tasks.winning_profile",
        "cios.tasks.research",
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
        "cios.tasks.pir.*": {"queue": "pir_scan"},
    },
    beat_schedule={
        "pir-daily-radar-scan": {
            "task": "cios.tasks.pir.daily_radar_scan",
            "schedule": 86400,  # every 24 hours
        },
        "quarterly-agency-intelligence-brief": {
            "task": "cios.tasks.research.generate_agency_intelligence_brief",
            "schedule": crontab(minute=0, hour=6, day_of_month=1, month_of_year="1,4,7,10"),
        },
    },
)
