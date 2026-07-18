"""
backend/app/core/rate_limit.py — In-memory rate limiter (per-IP, sliding window).
"""

import time
from collections import defaultdict
from typing import Dict, List

from backend.app.core import config

_rate_limit_store: Dict[str, List[float]] = defaultdict(list)

# Kopirano iz config-a na nivo modula da testovi mogu privremeno smanjiti limit
RATE_LIMIT_REQUESTS = config.RATE_LIMIT_REQUESTS
RATE_LIMIT_WINDOW = config.RATE_LIMIT_WINDOW


def _check_rate_limit(ip: str) -> bool:
    """Vraća True ako IP nije prešao limit. Čisti stare upise automatski."""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    calls = _rate_limit_store[ip]
    # Ukloni zahtjeve starije od window-a
    _rate_limit_store[ip] = [t for t in calls if t > window_start]
    if len(_rate_limit_store[ip]) >= RATE_LIMIT_REQUESTS:
        return False
    _rate_limit_store[ip].append(now)
    return True
