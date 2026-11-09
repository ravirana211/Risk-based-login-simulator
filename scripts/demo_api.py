"""Walk through the main login flows against a running API (simulation mode).

    RISKAUTH_SIM_MODE=1 uvicorn api.app:app --port 8000
    python scripts/demo_api.py --base http://localhost:8000
"""
from __future__ import annotations

import argparse
import json
import secrets
import urllib.error
import urllib.request

import pyotp

LONDON = {"ip": "81.2.69.1", "asn": 60100, "asn_type": "residential", "country": "GB",
          "city": "London", "lat": 51.51, "lon": -0.13}
LONDON_MOBILE = {**LONDON, "ip": "82.132.1.4", "asn": 60109, "asn_type": "mobile"}
TOKYO = {"ip": "126.0.0.7", "asn": 60190, "asn_type": "residential", "country": "JP",
         "city": "Tokyo", "lat": 35.68, "lon": 139.69}
AWS = {"ip": "3.5.140.2", "asn": 16509, "asn_type": "hosting", "country": "US",
       "city": "Ashburn", "lat": 39.04, "lon": -77.49}


def call(base: str, path: str, body: dict, geo: dict | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if geo:
        headers["X-Sim-Context"] = json.dumps(geo)
    req = urllib.request.Request(base + path, json.dumps(body).encode(), headers, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def show(title: str, status: int, body: dict) -> None:
    risk = body.get("risk", {})
    rules = ", ".join(f"{x['rule']} {x['points']:+g}" for x in risk.get("reasons", []))
    score = f"score {risk['score']:.0f}" if "score" in risk else ""
    print(f"{title:<42} HTTP {status}  {body.get('status'):<9} {score:<9} {rules}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    base = ap.parse_args().base
    user, pw = f"demo_{secrets.token_hex(3)}", "correct horse battery"
    laptop, phone = {"id": "dev-laptop-" + secrets.token_hex(4)}, {"id": "dev-phone-" + secrets.token_hex(4)}

    s, b = call(base, "/signup", {"username": user, "password": pw, "device": laptop}, LONDON)
    show(f"1. Sign up {user} (London, laptop)", s, b)
    totp = pyotp.TOTP(b["totp_secret"])

    show("2. Log in again, same laptop", *call(base, "/login", {"username": user, "password": pw, "device": laptop}, LONDON))
    show("3. Wrong password", *call(base, "/login", {"username": user, "password": "nope-nope", "device": laptop}, LONDON))

    s, b = call(base, "/login", {"username": user, "password": pw, "device": phone}, LONDON_MOBILE)
    show("4. New phone on mobile data", s, b)
    if b.get("status") == "step_up":
        show("   → enter TOTP code", *call(base, "/login/step-up", {"challenge_id": b["challenge_id"], "code": totp.now()}))
    show("5. Same phone again (now trusted)", *call(base, "/login", {"username": user, "password": pw, "device": phone}, LONDON_MOBILE))
    show("6. Tokyo, unknown device, minutes later", *call(base, "/login", {"username": user, "password": pw, "device": {"id": "dev-attacker-001"}}, TOKYO))
    show("7. Bot on AWS (headless)", *call(base, "/login", {"username": user, "password": pw, "device": {"id": "dev-bot-000001", "headless": True}}, AWS))


if __name__ == "__main__":
    main()
