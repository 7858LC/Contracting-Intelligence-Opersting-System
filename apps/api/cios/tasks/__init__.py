"""Celery task workers for async processing."""

import ssl
from urllib.parse import urlparse

from celery import Celery
from celery.schedules import crontab

from cios.config import settings

# Render's managed Redis (and most managed Redis providers) hands out a
# rediss:// (TLS) URL. Celery's redis backend refuses to start against
# rediss:// unless ssl_cert_reqs is explicitly configured — it won't infer
# a default the way redis-py's own client does — so this must be set
# whenever the URL uses that scheme, or the worker crashes on boot with
# "A rediss:// URL must have parameter ssl_cert_reqs...". CERT_NONE matches
# the managed-Redis providers' own guidance: the proxy-terminated TLS cert
# isn't meant to be verified against a public CA chain from inside the
# container network.
_uses_tls_redis = urlparse(settings.redis_url).scheme == "rediss"

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
    # kombu's redis transport issues a blocking BRPOP with this as its timeout,
    # then immediately reissues it if nothing arrived — Redis still wakes a
    # waiting BRPOP the instant a task is actually pushed, so this only
    # governs how often the worker re-polls while genuinely idle, not real
    # task pickup latency. Left at kombu's 1s default, an idle worker racks up
    # ~1 Redis command/sec against the broker for zero work; on a
    # per-command-billed provider (Upstash) that adds up continuously even
    # with no users on the platform.
    broker_transport_options={"polling_interval": 5},
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
    **(
        {
            "broker_use_ssl": {"ssl_cert_reqs": ssl.CERT_NONE},
            "redis_backend_use_ssl": {"ssl_cert_reqs": ssl.CERT_NONE},
        }
        if _uses_tls_redis
        else {}
    ),
)
