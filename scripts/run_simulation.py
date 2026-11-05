"""Generate synthetic logins, score them, and write metrics and threshold curves.

Usage: python scripts/run_simulation.py [--users 2000] [--days 30] [--seed 42]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from risksim.engine import Policy, RiskEngine, StepUpModel, run_stream  # noqa: E402
from risksim.generator import SimConfig, generate  # noqa: E402
from risksim.metrics import evaluate, scored_rows, sweep  # noqa: E402

FLAT_KEYS = ["step_up_at", "block_at", "method", "catch_rate", "false_positive_rate",
             "good_block_rate", "friction_sec_per_good_login", "missed_takeovers",
             "expected_abandons", "total_cost"]


def write_csv(path: Path, rows: list[dict], keys: list[str] | None = None) -> None:
    keys = keys or list(rows[0].keys())
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--users", type=int, default=2000)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=ROOT / "results")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    events = generate(SimConfig(n_users=args.users, days=args.days, seed=args.seed))
    engine = RiskEngine()
    rows = run_stream(events, engine)
    write_csv(args.out / "events_scored.csv", rows)

    summary = {"config": {"users": args.users, "days": args.days, "seed": args.seed,
                          "events": len(rows), "scored_events": len(scored_rows(rows))}}
    for method in ("otp", "passkey"):
        su = StepUpModel(method=method)
        summary[f"default_{method}"] = evaluate(rows, engine.policy, su)
        curve = sweep(rows, su, block_at=engine.policy.block_at)
        write_csv(args.out / f"sweep_{method}.csv", curve, FLAT_KEYS)
        best = min(curve, key=lambda m: m["total_cost"])
        summary[f"min_cost_{method}"] = {k: best[k] for k in FLAT_KEYS}

    # Score distribution by label (for histograms)
    hist: dict[str, list[int]] = {"good": [0] * 21, "attack": [0] * 21}
    for r in scored_rows(rows):
        hist[r["label"]][int(r["score"] // 5)] += 1
    summary["score_histogram_bins_of_5"] = hist
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2))

    d = summary["default_otp"]
    print(f"events: {len(rows):,}  scored (password ok, post-warmup): {summary['config']['scored_events']:,}")
    print(f"policy: step-up >= {engine.policy.step_up_at}, block >= {engine.policy.block_at}, OTP")
    print(f"  attack catch rate     {d['catch_rate']:.1%}  ({d['n_attack']} takeover attempts)")
    print(f"  good users challenged {d['false_positive_rate']:.2%}  (blocked {d['good_block_rate']:.2%})")
    print(f"  friction / good login {d['friction_sec_per_good_login']:.2f}s")
    print("  catch by scenario:", {k: f"{v:.0%}" for k, v in d["catch_by_scenario"].items()})
    print("  challenge rate by good scenario:",
          {k: f"{v:.1%}" for k, v in d["challenge_rate_by_good_scenario"].items()})
    print(f"results written to {args.out}")


if __name__ == "__main__":
    main()
