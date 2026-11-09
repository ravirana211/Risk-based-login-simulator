"""Runtime settings, read from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _flag(name: str, default: bool = False) -> bool:
    return os.environ.get(name, "1" if default else "0").lower() in ("1", "true", "yes")


@dataclass
class Settings:
    db_path: str = "riskauth.db"
    # Simulation mode trusts the X-Sim-Context header so a test client or the
    # attacker console can pretend to log in from anywhere. Never enable in production.
    sim_mode: bool = False
    # Trust X-Forwarded-For (only behind a proxy you control).
    trust_proxy: bool = False
    session_hours: int = 12
    challenge_minutes: int = 5
    challenge_attempts: int = 3
    # Optional MaxMind GeoLite2 databases for real IP intelligence.
    geoip_city_db: str | None = None
    geoip_asn_db: str | None = None
    admin_token: str | None = None  # enables /admin/* when set (always on in sim mode)

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_path=os.environ.get("RISKAUTH_DB", "riskauth.db"),
            sim_mode=_flag("RISKAUTH_SIM_MODE"),
            trust_proxy=_flag("RISKAUTH_TRUST_PROXY"),
            session_hours=int(os.environ.get("RISKAUTH_SESSION_HOURS", "12")),
            geoip_city_db=os.environ.get("RISKAUTH_GEOIP_CITY_DB"),
            geoip_asn_db=os.environ.get("RISKAUTH_GEOIP_ASN_DB"),
            admin_token=os.environ.get("RISKAUTH_ADMIN_TOKEN"),
        )
