"""PIR Scanner package — pluggable signal source adapters."""
from .base import BaseScanner, ScanResult, ScannedSignal
from .samgov import SAMGovScanner
from .usaspending import USASpendingScanner
from .jobs import JobBoardScanner

__all__ = [
    "BaseScanner",
    "ScanResult",
    "ScannedSignal",
    "SAMGovScanner",
    "USASpendingScanner",
    "JobBoardScanner",
]
