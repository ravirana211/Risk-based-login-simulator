"""Turn a raw login event plus history into named risk features."""
from __future__ import annotations

from dataclasses import dataclass

from .events import LoginEvent, haversine_km
from .state import RiskState


@dataclass
class Features:
    has_history: bool
    device_known: bool
    asn_type: str
    asn_new: bool
    country_new: bool
    km_from_last: float
    kmh_from_last: float
    acct_failures_1h: int
    ip_failures_1h: int
    ip_distinct_accounts_1h: int
    hour_deviation: float | None  # hours from user's usual time; None = not enough history
    hour_sd: float | None
    headless: bool


def extract(ev: LoginEvent, state: RiskState) -> Features:
    h = state.users.get(ev.username)
    has_history = h is not None and h.n_success > 0

    km = kmh = 0.0
    if has_history and h.last_success is not None:
        last_ts, last_lat, last_lon = h.last_success
        km = haversine_km(last_lat, last_lon, ev.lat, ev.lon)
        hours = max((ev.ts - last_ts).total_seconds() / 3600, 1 / 60)  # floor at one minute
        kmh = km / hours

    dev = sd = None
    prof = h.hour_profile() if has_history else None
    if prof is not None:
        mean, sd = prof
        hour = ev.ts.hour + ev.ts.minute / 60
        diff = abs(hour - mean) % 24
        dev = min(diff, 24 - diff)

    return Features(
        has_history=has_history,
        device_known=has_history and ev.device_id in h.devices,
        asn_type=ev.asn_type,
        asn_new=has_history and ev.asn not in h.asns,
        country_new=has_history and ev.country not in h.countries,
        km_from_last=km,
        kmh_from_last=kmh,
        acct_failures_1h=state.account_failures_recent(ev.username, ev.ts),
        ip_failures_1h=state.ip_failures_recent(ev.ip, ev.ts),
        ip_distinct_accounts_1h=state.ip_distinct_accounts_recent(ev.ip, ev.ts),
        hour_deviation=dev,
        hour_sd=sd,
        headless=ev.headless,
    )
