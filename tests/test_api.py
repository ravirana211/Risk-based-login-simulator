import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pyotp  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.app import create_app  # noqa: E402
from api.config import Settings  # noqa: E402

LONDON = {"ip": "81.2.69.1", "asn": 60100, "asn_type": "residential", "country": "GB",
          "city": "London", "lat": 51.51, "lon": -0.13}
LONDON_NEW_ISP = {**LONDON, "ip": "81.2.70.9", "asn": 60101}
TOKYO = {"ip": "126.0.0.7", "asn": 60190, "asn_type": "residential", "country": "JP",
         "city": "Tokyo", "lat": 35.68, "lon": 139.69}
HOME_DEVICE = {"id": "dev-home-laptop-01"}
NEW_DEVICE = {"id": "dev-new-phone-002"}
DENIED = {"status": "denied", "message": "We couldn't sign you in with those details."}


class Clock:
    def __init__(self):
        self.now = datetime(2026, 11, 5, 9, 0, 0)

    def __call__(self):
        return self.now

    def advance(self, **kw):
        self.now += timedelta(**kw)


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "t.db")
        self.clock = Clock()
        self.client = self.make_client()
        r = self.signup("alice", "correct horse battery", LONDON, HOME_DEVICE)
        self.assertEqual(r.status_code, 201, r.text)
        self.secret = r.json()["totp_secret"]

    def tearDown(self):
        for c in self.clients:
            c.app.state.service.db.conn.close()
        self.tmp.cleanup()

    def make_client(self, sim_mode=True):
        if not hasattr(self, "clients"):
            self.clients = []
        c = TestClient(create_app(Settings(db_path=self.db, sim_mode=sim_mode), clock=self.clock))
        self.clients.append(c)
        return c

    def _post(self, path, body, geo, client=None):
        return (client or self.client).post(path, json=body, headers={"X-Sim-Context": json.dumps(geo)})

    def signup(self, u, p, geo, device):
        return self._post("/signup", {"username": u, "password": p, "device": device}, geo)

    def login(self, geo, device, password="correct horse battery", user="alice", client=None):
        return self._post("/login", {"username": user, "password": password, "device": device}, geo, client)

    def code(self, offset_steps=0):
        t = self.clock.now.replace(tzinfo=timezone.utc) + timedelta(seconds=30 * offset_steps)
        return pyotp.TOTP(self.secret).at(t)

    def step_up(self, cid, code):
        return self.client.post("/login/step-up", json={"challenge_id": cid, "code": code})

    # --- flows ------------------------------------------------------------
    def test_signup_returns_working_session_and_totp_uri(self):
        r = self.signup("bob", "another good pass", LONDON, HOME_DEVICE).json()
        self.assertTrue(r["otpauth_uri"].startswith("otpauth://totp/"))
        me = self.client.get("/me", headers={"Authorization": f"Bearer {r['session_token']}"})
        self.assertEqual(me.json()["username"], "bob")

    def test_duplicate_and_weak_signup_rejected(self):
        self.assertEqual(self.signup("alice", "whatever123", LONDON, HOME_DEVICE).status_code, 409)
        self.assertEqual(self.signup("carol", "short", LONDON, HOME_DEVICE).status_code, 400)

    def test_known_device_at_home_is_allowed(self):
        self.clock.advance(hours=3)
        r = self.login(LONDON, HOME_DEVICE)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")
        self.assertEqual(r.json()["risk"]["decision"], "allow")

    def test_new_device_steps_up_then_becomes_trusted(self):
        self.clock.advance(hours=3)
        r = self.login(LONDON_NEW_ISP, NEW_DEVICE).json()
        self.assertEqual(r["status"], "step_up")
        rules = {x["rule"] for x in r["risk"]["reasons"]}
        self.assertTrue({"new_device", "asn_new"} <= rules)

        bad = self.step_up(r["challenge_id"], "000000")
        self.assertEqual(bad.status_code, 401)
        self.assertEqual(bad.json()["attempts_left"], 2)

        ok = self.step_up(r["challenge_id"], self.code())
        self.assertEqual(ok.status_code, 200, ok.text)
        self.assertIn("session_token", ok.json())

        self.clock.advance(hours=2)
        again = self.login(LONDON_NEW_ISP, NEW_DEVICE).json()
        self.assertEqual(again["status"], "ok")  # device and ISP are now known

    def test_impossible_travel_is_blocked_with_generic_message(self):
        self.clock.advance(hours=1)
        r = self.login(TOKYO, NEW_DEVICE)
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json(), DENIED)
        ev = self.client.get("/admin/events").json()[0]
        self.assertEqual((ev["decision"], ev["outcome"]), ("block", "blocked"))
        self.assertIn("impossible_travel", ev["reasons"])

    def test_wrong_password_looks_like_block(self):
        self.clock.advance(hours=3)
        r = self.login(LONDON, HOME_DEVICE, password="wrong password")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json(), DENIED)

    def test_unknown_user_gets_same_response(self):
        r = self.login(LONDON, HOME_DEVICE, user="nobody")
        self.assertEqual((r.status_code, r.json()), (401, DENIED))

    def test_risky_wrong_password_gets_decoy_challenge(self):
        self.clock.advance(hours=3)
        r = self.login(LONDON_NEW_ISP, NEW_DEVICE, password="leaked but wrong").json()
        self.assertEqual(r["status"], "step_up")  # indistinguishable from a real challenge
        res = self.step_up(r["challenge_id"], self.code())
        self.assertEqual(res.status_code, 401)  # even the right code can't pass it

    def test_totp_code_cannot_be_replayed(self):
        self.clock.advance(hours=3)
        c1 = self.login(LONDON_NEW_ISP, NEW_DEVICE).json()["challenge_id"]
        code = self.code()
        self.assertEqual(self.step_up(c1, code).status_code, 200)
        other_isp = {**LONDON, "ip": "81.2.71.3", "asn": 60102}
        c2 = self.login(other_isp, {"id": "dev-third-device-3"}).json()["challenge_id"]
        self.assertEqual(self.step_up(c2, code).status_code, 401)

    def test_three_wrong_codes_close_the_challenge(self):
        self.clock.advance(hours=3)
        cid = self.login(LONDON_NEW_ISP, NEW_DEVICE).json()["challenge_id"]
        codes = [self.step_up(cid, "111111").status_code for _ in range(3)]
        self.assertEqual(codes, [401, 401, 410])
        self.assertEqual(self.step_up(cid, self.code()).status_code, 410)
        ev = self.client.get("/admin/events").json()[0]
        self.assertEqual(ev["outcome"], "challenge_failed")

    def test_challenge_expires(self):
        self.clock.advance(hours=3)
        cid = self.login(LONDON_NEW_ISP, NEW_DEVICE).json()["challenge_id"]
        self.clock.advance(minutes=6)
        r = self.step_up(cid, self.code())
        self.assertEqual((r.status_code, r.json()["status"]), (410, "challenge_expired"))

    def test_history_survives_restart(self):
        self.clock.advance(hours=3)
        cid = self.login(LONDON_NEW_ISP, NEW_DEVICE).json()["challenge_id"]
        self.step_up(cid, self.code())
        fresh = self.make_client()  # new process, same database
        self.clock.advance(hours=2)
        self.assertEqual(self.login(LONDON_NEW_ISP, NEW_DEVICE, client=fresh).json()["status"], "ok")

    def test_logout_ends_session(self):
        tok = self.login(LONDON, HOME_DEVICE).json()["session_token"]
        h = {"Authorization": f"Bearer {tok}"}
        self.assertEqual(self.client.post("/logout", headers=h).status_code, 204)
        self.assertEqual(self.client.get("/me", headers=h).status_code, 401)

    def test_sim_header_and_admin_ignored_outside_sim_mode(self):
        prod = self.make_client(sim_mode=False)
        r = self.login(TOKYO, HOME_DEVICE, client=prod).json()
        self.assertNotIn("reasons", r.get("risk", {}))  # rules are not exposed
        self.assertEqual(prod.get("/admin/events").status_code, 403)


if __name__ == "__main__":
    unittest.main()
