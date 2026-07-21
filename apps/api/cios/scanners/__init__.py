"""PIR Scanner package — pluggable signal source adapters."""

from .base import BaseScanner, ScannedSignal, ScanResult
from .jobs import JobBoardScanner
from .samgov import SAMGovScanner
from .usaspending import USASpendingScanner

__all__ = [
    "BaseScanner",
    "ScanResult",
    "ScannedSignal",
    "SAMGovScanner",
    "USASpendingScanner",
    "JobBoardScanner",
]
