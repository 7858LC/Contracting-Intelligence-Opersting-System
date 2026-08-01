"""Usage-limit enforcement — the metering half of core/features.py's
PLAN_FEATURES quotas (tracked_companies, watchlist_slots, saved_searches,
ai_reports_per_month, bulk_scan_jobs_per_month, seats).

Previously these numbers were sold on the pricing page and returned by
GET /subscriptions but never counted against anything — a tenant on any
plan could create an unlimited number of tracked companies, watchlists,
saved searches, AI analyses, or bulk scans, and invite an unlimited
number of teammates, regardless of what they paid for. This module is
the fix: a real COUNT against the tenant's own rows, checked before the
row that would exceed the limit gets created.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from cios.core.features import plan_limit


def enforce_usage_limit_value(plan: str, metric: str, count: int, *, label: str) -> None:
    """-1 in PLAN_FEATURES means unlimited (Enterprise's convention
    throughout that table). Split out from enforce_usage_limit() below so
    callers that need to sum more than one query's count (e.g. seats:
    active members + outstanding invites, two different tables) can
    compute the total themselves rather than needing count_query to
    express a cross-table sum."""
    limit = plan_limit(plan, metric)
    if limit < 0:
        return
    if count >= limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"You've reached your plan's limit of {limit} {label}. "
            "Upgrade your subscription to add more.",
        )


async def enforce_usage_limit(
    db: AsyncSession, plan: str, metric: str, count_query: Select, *, label: str
) -> None:
    """count_query must be a `select(func.count(...))` already filtered to
    the requesting tenant (and, for the two monthly metrics, to the
    current calendar month — see current_month_start())."""
    count = (await db.execute(count_query)).scalar_one()
    enforce_usage_limit_value(plan, metric, count, label=label)


def current_month_start() -> datetime:
    now = datetime.now(UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
