"""Weighted-rule risk engine and the allow / step-up / block policy."""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field

from .events import LoginEvent
from .signals import Features, extract
from .state import RiskState

ALLOW, STEP_UP, BLOCK = "allow", "step_up", "block"


@dataclass
class RuleWeights:
    """Points added to the 0-100 risk score when a rule fires."""

    new_device: float = 25
    known_device: float = -15  # trust credit
    asn_hosting: float = 30
    asn_tor: float = 45
    asn_new: float = 10
    country_new: float = 15
    impossible_travel: float = 35
    impossible_travel_kmh: float = 1000  # faster than a commercial flight
    impossible_travel_min_km: float = 500  # ignore city-level geo-IP noise
    acct_failures: float = 15  # >= acct_failures_at failed passwords on this account in 1h
    acct_failures_at: int = 3
    acct_failures_heavy: float = 30  # >= 10 failures: brute force
    ip_spray: float = 35  # one IP trying many different accounts
    ip_spray_at: int = 5
    headless: float = 30
    odd_hour: float = 10
    odd_hour_min_dev: float = 4.0  # hours
    odd_hour_sigmas: float = 2.5


@dataclass
class Policy:
    step_up_at: float = 30
    block_at: float = 70

    def decide(self, score: float) -> str:
        if score >= self.block_at:
            return BLOCK
        if score >= self.step_up_at:
            return STEP_UP
        return ALLOW


@dataclass
class RiskEngine:
    weights: RuleWeights = field(default_factory=RuleWeights)
    policy: Policy = field(default_factory=Policy)

    def score(self, f: Features) -> tuple[float, list[tuple[str, float]]]:
        """Return (score clamped to 0-100, list of (rule, points) that fired)."""
        w = self.weights
        hits: list[tuple[str, float]] = []

        if f.device_known:
            hits.append(("known_device", w.known_device))
        else:
            hits.append(("new_device", w.new_device))

        if f.asn_type == "tor":
            hits.append(("asn_tor", w.asn_tor))
        elif f.asn_type == "hosting":
            hits.append(("asn_hosting", w.asn_hosting))
        if f.asn_new:
            hits.append(("asn_new", w.asn_new))
        if f.country_new:
            hits.append(("country_new", w.country_new))

        if f.kmh_from_last > w.impossible_travel_kmh and f.km_from_last > w.impossible_travel_min_km:
            hits.append(("impossible_travel", w.impossible_travel))

        if f.acct_failures_1h >= 10:
            hits.append(("acct_failures_heavy", w.acct_failures_heavy))
        elif f.acct_failures_1h >= w.acct_failures_at:
            hits.append(("acct_failures", w.acct_failures))
        if f.ip_distinct_accounts_1h >= w.ip_spray_at:
            hits.append(("ip_spray", w.ip_spray))

        if f.headless:
            hits.append(("headless", w.headless))

        if f.hour_deviation is not None and f.hour_sd is not None:
            if f.hour_deviation > max(w.odd_hour_min_dev, w.odd_hour_sigmas * f.hour_sd):
                hits.append(("odd_hour", w.odd_hour))

        total = sum(p for _, p in hits)
        return max(0.0, min(100.0, total)), hits

    def evaluate(self, ev: LoginEvent, state: RiskState) -> dict:
        f = extract(ev, state)
        score, hits = self.score(f)
        return {"features": f, "score": score, "reasons": hits, "decision": self.policy.decide(score)}


@dataclass
class StepUpModel:
    """How a step-up challenge plays out. Used for both simulation and metrics."""

    method: str = "otp"  # "otp" | "passkey"
    friction_seconds: dict = field(default_factory=lambda: {"otp": 30.0, "passkey": 6.0})
    good_abandon: dict = field(default_factory=lambda: {"otp": 0.04, "passkey": 0.01})
    # Chance an attacker who has the password also gets past the challenge
    # (phished OTP, SIM swap, real-time relay). Passkeys are phishing resistant.
    attacker_pass: dict = field(default_factory=lambda: {"otp": 0.10, "passkey": 0.0})
    block_seconds: float = 300.0  # good user locked out: support call / account recovery

    @property
    def seconds(self) -> float:
        return self.friction_seconds[self.method]

    @property
    def abandon(self) -> float:
        return self.good_abandon[self.method]

    @property
    def attack_pass(self) -> float:
        return self.attacker_pass[self.method]


def run_stream(
    events: list[LoginEvent],
    engine: RiskEngine | None = None,
    stepup: StepUpModel | None = None,
    seed: int = 7,
) -> list[dict]:
    """Score events in time order, play out decisions, and update history as they go.

    History (known devices, ASNs, last location) is learned from logins that
    actually succeed under this engine's policy, as it would be in production.
    Returns one flat row per event, ready for CSV and metrics.
    """
    engine = engine or RiskEngine()
    stepup = stepup or StepUpModel()
    rng = random.Random(seed)
    state = RiskState()
    rows = []
    for ev in sorted(events, key=lambda e: e.ts):
        out = engine.evaluate(ev, state)
        decision = out["decision"]
        success = False
        if ev.password_ok and decision != BLOCK:
            if decision == ALLOW:
                success = True
            else:
                p = (1 - stepup.abandon) if ev.label == "good" else stepup.attack_pass
                success = rng.random() < p
        state.record(ev, success)

        row = asdict(ev)
        row["ts"] = ev.ts.isoformat()
        row.update({f"f_{k}": v for k, v in asdict(out["features"]).items()})
        row["score"] = out["score"]
        row["reasons"] = ";".join(f"{n}:{p:+g}" for n, p in out["reasons"])
        row["decision"] = decision
        row["success"] = success
        rows.append(row)
    return rows
