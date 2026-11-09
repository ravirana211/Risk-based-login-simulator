# Risk-based login simulator

**Question:** how do you stop account takeover without annoying good users?

Every login gets a 0–100 risk score from weighted rules. The policy then **allows** it, asks for a **step-up** (OTP or passkey), or **blocks** it. A synthetic traffic generator produces good users and labelled attacks, so we can measure the trade-off.

The simulator is pure Python 3.11+ (standard library only). The login API adds FastAPI and pyotp.

```bash
python scripts/run_simulation.py            # 2,000 users x 30 days, ~20s
pip install -r requirements.txt
python -m unittest discover -s tests        # engine + API tests
```

## Login API

A FastAPI service that puts the same `RiskEngine` in front of real signup and login.

```bash
RISKAUTH_SIM_MODE=1 uvicorn api.app:app --port 8000   # interactive docs at /docs
python scripts/demo_api.py                           # walks through the main flows
```

| Endpoint | What it does |
|---|---|
| `POST /signup` | Create account; returns a session plus a TOTP secret and `otpauth://` URI for an authenticator app. The signup device and network become the first known history. |
| `POST /login` | Scores the attempt. Returns `ok` + session, `step_up` + `challenge_id`, or `401 denied` |
| `POST /login/step-up` | Verify a 6-digit TOTP code. 3 attempts, 5-minute expiry, each code works only once. Passing trusts the device. |
| `GET /me`, `POST /logout` | Bearer-token session |
| `GET /admin/events`, `GET /admin/policy` | Login log with score, rule reasons, decision and outcome (for the dashboard) |

Design choices:
- **One source of truth.** Every attempt is stored in `login_events`. The in-memory `RiskState` is rebuilt from that table at startup.
- **No credential oracle.** A block returns the same `401` as a wrong password. A risky attempt with a wrong password gets a decoy challenge that can never pass, so bots can't use the step-up prompt to test which leaked passwords are valid. Unknown usernames are checked against a dummy hash so response timing doesn't reveal which accounts exist.
- **Learning only from completed logins.** A device or network becomes trusted only after an allowed login or a passed step-up.
- **Simulation mode** (`RISKAUTH_SIM_MODE=1`) trusts an `X-Sim-Context` header (IP, ASN, geo, timestamp, ground-truth label), so the attacker console can replay scenarios from anywhere. It also returns rule reasons and opens `/admin/*`. Never enable it in production.
- **IP intelligence** is pluggable: `StaticIpIntel` for local development, `MaxMindIpIntel` with GeoLite2 `.mmdb` files (`RISKAUTH_GEOIP_CITY_DB`, `RISKAUTH_GEOIP_ASN_DB`) for real lookups.

Before production: encrypt TOTP secrets at rest, put the API behind HTTPS, add CSRF protection if you use cookies, add a per-IP rate limit in front of `/login`, and switch SQLite to Postgres.

## Layout

| Path | What it does |
|---|---|
| `risksim/events.py` | `LoginEvent` type, haversine distance |
| `risksim/state.py` | Per-user history (known devices/ASNs/countries, last location, login-hour profile) and 1h sliding-window failure counters |
| `risksim/signals.py` | Event + history → `Features` |
| `risksim/engine.py` | `RuleWeights`, `Policy` (allow/step-up/block), `RiskEngine`, `StepUpModel`, `run_stream()` |
| `risksim/generator.py` | Synthetic users, personas and attack scenarios |
| `risksim/metrics.py` | Catch rate, false-positive rate, friction, cost, threshold sweep |
| `scripts/run_simulation.py` | End-to-end run → `results/` |
| `api/` | FastAPI login API: `app.py` (routes), `service.py` (auth + risk logic), `db.py`, `security.py`, `ipintel.py` |
| `scripts/demo_api.py` | Walks through allow / step-up / block against a running API |

The login API imports `RiskEngine` and `RiskState` directly, so live logins and the simulator score with the same code.

## Signals and default weights

| Rule | Points |
|---|---|
| New device / known device | +25 / −15 |
| Hosting ASN / Tor | +30 / +45 |
| ASN new for this user | +10 |
| Country new for this user | +15 |
| Impossible travel (>1000 km/h and >500 km) | +35 |
| ≥3 / ≥10 failed passwords on account in 1h | +15 / +30 |
| IP tried ≥5 distinct accounts in 1h | +35 |
| Headless browser | +30 |
| Login hour > max(4h, 2.5σ) from user's norm | +10 |

Default policy: step-up at ≥30, block at ≥70.

## Synthetic traffic

**Good users:** home city/ISP, 1–3 devices, personal login-hour profile. Personas that cause false positives: travellers (6%), VPN users (7%), new phones (12%), shift workers (8%), typos (6% of logins).

**Attacks (after a 7-day warm-up):** credential stuffing (datacenter/Tor, bots), smart stuffing (rotating residential proxies), brute force, impossible travel, new device at 3am, local attacker (same city, normal hours).

## Metrics

Computed on **password-correct, post-warm-up** attempts. A wrong password fails anyway, so the engine's decision only matters when the password is right.

- **Catch rate**: share of takeover attempts blocked, or stepped up and failing the challenge (OTP lets ~10% of attackers through, passkeys 0%).
- **False-positive rate**: share of good logins challenged or blocked.
- **Friction**: seconds added per good login (OTP 30s, passkey 6s, block 300s).
- **Cost**: missed takeovers × $250 + friction seconds × $0.02 + abandons × $5. All tunable.

## Results (seed 42, 2,000 users, 30 days)

| | Default (≥30 / ≥70, OTP) |
|---|---|
| Takeover attempts caught | 91.3% |
| Good logins challenged | 1.75% (0.21% blocked) |
| Friction per good login | 1.1s |

Findings:
- **VPN users** account for most false positives: 55% of their logins are challenged.
- **Local attackers** (same city, normal hours, residential IP) are the hardest case: 66% caught.
- Moving step-up from 30 to 22 is the lowest-cost OTP policy. Passkeys reach a much lower cost because attackers cannot relay them.

## Known limitations / next steps

- Every attack in the generator uses a new device, so "new device" separates attackers too cleanly. Add stolen-session and malware-on-known-device scenarios.
- Sweeps re-threshold fixed scores. History is learned once, under the default policy.
- Validate against the public RBA dataset (Wiefling et al.) before trusting the numbers.
- ~~Phase 3: login API with TOTP step-up~~ done. Next: web UI + attacker console, live dashboard, WebAuthn passkeys, optional logistic-regression model.
