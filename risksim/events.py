"""Core data types shared by the engine, the generator and the evaluation code."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

# ASN categories the engine understands.
ASN_TYPES = ("residential", "mobile", "hosting", "tor")


@dataclass
class LoginEvent:
    """One login attempt, as the auth server would see it.

    `label`, `scenario` and `warmup` are ground truth for evaluation only.
    The risk engine must never read them.
    """

    event_id: int
    ts: datetime  # UTC
    username: str
    ip: str
    asn: int
    asn_type: str  # one of ASN_TYPES
    country: str
    city: str
    lat: float
    lon: float
    device_id: str
    headless: bool
    password_ok: bool
    # --- ground truth (never read by the engine) ---
    label: str = "good"  # "good" | "attack"
    scenario: str = "normal"
    warmup: bool = False


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in kilometres."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
