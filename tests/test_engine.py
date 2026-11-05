import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from risksim.engine import ALLOW, BLOCK, STEP_UP, Policy, RiskEngine, StepUpModel, run_stream  # noqa: E402
from risksim.events import LoginEvent, haversine_km  # noqa: E402
from risksim.generator import SimConfig, generate  # noqa: E402
from risksim.metrics import evaluate  # noqa: E402
from risksim.state import RiskState  # noqa: E402

T0 = datetime(2026, 10, 1, 9)
LONDON = ("London", "GB", 51.51, -0.13)
TOKYO = ("Tokyo", "JP", 35.68, 139.69)


def ev(ts, city=LONDON, device="d1", asn=100, asn_type="residential", ok=True,
       user="alice", ip="1.1.1.1", headless=False, label="good"):
    return LoginEvent(event_id=0, ts=ts, username=user, ip=ip, asn=asn, asn_type=asn_type,
                      country=city[1], city=city[0], lat=city[2], lon=city[3], device_id=device,
                      headless=headless, password_ok=ok, label=label)


def seeded_state() -> RiskState:
    s = RiskState()
    for d in range(10):
        s.record(ev(T0 + timedelta(days=d)), success=True)
    return s


class TestGeo(unittest.TestCase):
    def test_haversine_london_tokyo(self):
        self.assertAlmostEqual(haversine_km(*LONDON[2:], *TOKYO[2:]), 9560, delta=60)


class TestEngine(unittest.TestCase):
    def setUp(self):
        self.engine = RiskEngine()
        self.state = seeded_state()

    def test_known_device_at_home_is_allowed(self):
        out = self.engine.evaluate(ev(T0 + timedelta(days=11)), self.state)
        self.assertEqual(out["decision"], ALLOW)

    def test_impossible_travel_new_device_is_blocked(self):
        out = self.engine.evaluate(
            ev(T0 + timedelta(days=9, hours=1), city=TOKYO, device="evil", asn=999), self.state)
        names = [n for n, _ in out["reasons"]]
        self.assertIn("impossible_travel", names)
        self.assertEqual(out["decision"], BLOCK)

    def test_new_device_from_new_isp_steps_up(self):
        out = self.engine.evaluate(ev(T0 + timedelta(days=11), device="new", asn=101), self.state)
        self.assertEqual(out["decision"], STEP_UP)

    def test_odd_hour_fires(self):
        out = self.engine.evaluate(ev(T0 + timedelta(days=11, hours=-6)), self.state)
        self.assertIn("odd_hour", [n for n, _ in out["reasons"]])

    def test_ip_spray_detected(self):
        s = RiskState()
        for i in range(6):
            s.record(ev(T0 + timedelta(seconds=10 * i), user=f"u{i}", ip="6.6.6.6", ok=False), False)
        out = self.engine.evaluate(ev(T0 + timedelta(minutes=2), user="u9", ip="6.6.6.6"), s)
        self.assertIn("ip_spray", [n for n, _ in out["reasons"]])

    def test_policy_bands(self):
        p = Policy(step_up_at=30, block_at=70)
        self.assertEqual([p.decide(x) for x in (29, 30, 69, 70)], [ALLOW, STEP_UP, STEP_UP, BLOCK])


class TestMetrics(unittest.TestCase):
    def test_expected_value_accounting(self):
        rows = [
            {"password_ok": True, "warmup": False, "label": "attack", "scenario": "a", "score": 50},
            {"password_ok": True, "warmup": False, "label": "attack", "scenario": "a", "score": 90},
            {"password_ok": True, "warmup": False, "label": "good", "scenario": "n", "score": 50},
            {"password_ok": True, "warmup": False, "label": "good", "scenario": "n", "score": 0},
            {"password_ok": False, "warmup": False, "label": "good", "scenario": "n", "score": 99},
        ]
        m = evaluate(rows, Policy(30, 70), StepUpModel(method="otp"))
        self.assertAlmostEqual(m["catch_rate"], (0.9 + 1.0) / 2)
        self.assertAlmostEqual(m["false_positive_rate"], 0.5)
        self.assertAlmostEqual(m["friction_sec_per_good_login"], 15.0)


class TestGenerator(unittest.TestCase):
    def test_deterministic_and_labelled(self):
        cfg = SimConfig(n_users=60, days=12, seed=1, stuffing_campaigns=1, smart_stuffing_campaigns=1,
                        brute_force_targets=1, impossible_travel_victims=3,
                        new_device_3am_victims=3, local_attacker_victims=3)
        a, b = generate(cfg), generate(cfg)
        self.assertEqual([(e.ts, e.username, e.device_id) for e in a],
                         [(e.ts, e.username, e.device_id) for e in b])
        self.assertTrue(any(e.label == "attack" for e in a))
        self.assertFalse(any(e.label == "attack" and e.warmup for e in a))
        rows = run_stream(a)
        self.assertEqual(len(rows), len(a))


if __name__ == "__main__":
    unittest.main()
