"""Catch rate, false-positive rate, friction, and threshold sweeps.

Metrics are computed on attempts where the password was correct and that fall
after the warm-up period. A wrong password fails whatever the risk engine
says, so the engine's decision only matters when the password is right.

Step-up outcomes use expected values, not coin flips, so curves are smooth:
an attacker who is stepped up counts as (1 - attacker_pass) of a catch, and a
good user who is stepped up pays the challenge's friction seconds.

Approximation: history (known devices etc.) was learned under the reference
policy used in `run_stream`. A sweep re-applies thresholds to fixed scores
and does not re-learn history for each threshold.
"""
from __future__ import annotations

from collections import defaultdict

from .engine import ALLOW, BLOCK, STEP_UP, Policy, StepUpModel


def scored_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["password_ok"] and not r["warmup"]]


def evaluate(rows: list[dict], policy: Policy, stepup: StepUpModel | None = None,
             loss_per_ato: float = 250.0, cost_per_friction_sec: float = 0.02,
             cost_per_abandon: float = 5.0) -> dict:
    stepup = stepup or StepUpModel()
    rows = scored_rows(rows)
    good = attack = 0
    caught = challenged = blocked_good = friction = abandons = 0.0
    by_scn: dict[str, list[float]] = defaultdict(lambda: [0, 0.0])  # [n, caught]
    fp_scn: dict[str, list[float]] = defaultdict(lambda: [0, 0.0])  # [n, challenged]

    for r in rows:
        d = policy.decide(r["score"])
        if r["label"] == "attack":
            attack += 1
            c = 1.0 if d == BLOCK else (1 - stepup.attack_pass) if d == STEP_UP else 0.0
            caught += c
            by_scn[r["scenario"]][0] += 1
            by_scn[r["scenario"]][1] += c
        else:
            good += 1
            ch = d != ALLOW
            challenged += ch
            fp_scn[r["scenario"]][0] += 1
            fp_scn[r["scenario"]][1] += ch
            if d == STEP_UP:
                friction += stepup.seconds
                abandons += stepup.abandon
            elif d == BLOCK:
                friction += stepup.block_seconds
                blocked_good += 1

    missed = attack - caught
    cost = missed * loss_per_ato + friction * cost_per_friction_sec + abandons * cost_per_abandon
    return {
        "step_up_at": policy.step_up_at,
        "block_at": policy.block_at,
        "method": stepup.method,
        "n_good": good,
        "n_attack": attack,
        "catch_rate": caught / attack if attack else 0.0,
        "false_positive_rate": challenged / good if good else 0.0,
        "good_block_rate": blocked_good / good if good else 0.0,
        "friction_sec_per_good_login": friction / good if good else 0.0,
        "expected_abandons": abandons,
        "missed_takeovers": missed,
        "total_cost": cost,
        "catch_by_scenario": {k: v[1] / v[0] for k, v in sorted(by_scn.items())},
        "attacks_by_scenario": {k: v[0] for k, v in sorted(by_scn.items())},
        "challenge_rate_by_good_scenario": {k: v[1] / v[0] for k, v in sorted(fp_scn.items())},
        "good_by_scenario": {k: v[0] for k, v in sorted(fp_scn.items())},
    }


def sweep(rows: list[dict], stepup: StepUpModel | None = None, block_at: float = 70,
          thresholds=range(0, 102, 2), **cost_kw) -> list[dict]:
    """Tighten the policy: move the step-up threshold down from 100 to 0.

    The block threshold stays fixed unless the step-up threshold rises above it.
    """
    out = []
    for t in thresholds:
        m = evaluate(rows, Policy(step_up_at=t, block_at=max(block_at, t)), stepup, **cost_kw)
        out.append(m)
    return out
