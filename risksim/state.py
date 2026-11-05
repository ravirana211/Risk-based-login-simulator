"""Per-user history and sliding-window counters the risk engine scores against."""
from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .events import LoginEvent


@dataclass
class UserHistory:
    devices: set[str] = field(default_factory=set)
    asns: set[int] = field(default_factory=set)
    countries: set[str] = field(default_factory=set)
    last_success: tuple[datetime, float, float] | None = None  # (ts, lat, lon)
    n_success: int = 0
    # Running sums of login hour as an angle on a 24h clock (circular stats).
    hour_sin: float = 0.0
    hour_cos: float = 0.0

    def add_hour(self, ts: datetime) -> None:
        angle = 2 * math.pi * (ts.hour + ts.minute / 60) / 24
        self.hour_sin += math.sin(angle)
        self.hour_cos += math.cos(angle)

    def hour_profile(self) -> tuple[float, float] | None:
        """Return (mean_hour, circular_sd_hours), or None if there is too little history."""
        if self.n_success < 5:
            return None
        s, c = self.hour_sin / self.n_success, self.hour_cos / self.n_success
        r = min(max(math.hypot(s, c), 1e-9), 1.0)
        mean = (math.atan2(s, c) % (2 * math.pi)) * 24 / (2 * math.pi)
        sd = math.sqrt(-2 * math.log(r)) * 24 / (2 * math.pi)
        return mean, sd


class RiskState:
    """Everything the engine remembers between logins.

    In the web app this lives in the database. In the simulator it is in memory.
    """

    def __init__(self, window: timedelta = timedelta(hours=1)):
        self.window = window
        self.users: dict[str, UserHistory] = defaultdict(UserHistory)
        self.account_failures: dict[str, deque[datetime]] = defaultdict(deque)
        self.ip_failures: dict[str, deque[datetime]] = defaultdict(deque)
        self.ip_accounts: dict[str, deque[tuple[datetime, str]]] = defaultdict(deque)

    # -- window helpers -------------------------------------------------
    def _trim(self, dq: deque, now: datetime) -> None:
        cutoff = now - self.window
        while dq and (dq[0][0] if isinstance(dq[0], tuple) else dq[0]) < cutoff:
            dq.popleft()

    def account_failures_recent(self, username: str, now: datetime) -> int:
        dq = self.account_failures[username]
        self._trim(dq, now)
        return len(dq)

    def ip_failures_recent(self, ip: str, now: datetime) -> int:
        dq = self.ip_failures[ip]
        self._trim(dq, now)
        return len(dq)

    def ip_distinct_accounts_recent(self, ip: str, now: datetime) -> int:
        dq = self.ip_accounts[ip]
        self._trim(dq, now)
        return len({u for _, u in dq})

    # -- updates ---------------------------------------------------------
    def record(self, ev: LoginEvent, success: bool) -> None:
        """Update state after an attempt. `success` = the user ended up logged in."""
        self.record_attempt(ev)
        if success:
            self.record_success(ev)

    def record_attempt(self, ev: LoginEvent) -> None:
        """Count the attempt in the sliding windows (call once per attempt)."""
        self.ip_accounts[ev.ip].append((ev.ts, ev.username))
        if not ev.password_ok:
            self.account_failures[ev.username].append(ev.ts)
            self.ip_failures[ev.ip].append(ev.ts)

    def record_success(self, ev: LoginEvent) -> None:
        """Learn from a completed login. In the API this can happen after a step-up."""
        h = self.users[ev.username]
        h.devices.add(ev.device_id)
        h.asns.add(ev.asn)
        h.countries.add(ev.country)
        h.last_success = (ev.ts, ev.lat, ev.lon)
        h.n_success += 1
        h.add_hour(ev.ts)
