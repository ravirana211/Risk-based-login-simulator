"""Auth logic: signup, risk-scored login, TOTP step-up, sessions.

Kept separate from the HTTP layer so it can be tested and reused directly.
Risk state lives in memory (the same `RiskState` the simulator uses) and is
rebuilt from the `login_events` table at startup, so there is one source of
truth and the live engine behaves exactly like the simulated one.
"""
from __future__ import annotations

import hmac
import re
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

import pyotp

from risksim.engine import ALLOW, BLOCK, STEP_UP, RiskEngine
from risksim.events import LoginEvent
from risksim.state import RiskState

from .config import Settings
from .db import Database
from .ipintel import IpInfo
from .security import DUMMY_HASH, hash_password, new_token, token_hash, verify_password

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.@-]{3,64}$")
ISSUER = "RiskLoginSim"


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class LoginContext:
    """What the server knows about the request, apart from the credentials."""

    ip: str
    info: IpInfo
    device_id: str
    headless: bool = False
    ts: datetime | None = None  # override only in simulation mode
    sim_label: str | None = None


class AuthError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, **extra):
        super().__init__(message)
        self.code, self.message, self.status, self.extra = code, message, status, extra


class AuthService:
    def __init__(self, db: Database, settings: Settings, engine: RiskEngine | None = None,
                 clock: Callable[[], datetime] = utcnow):
        self.db, self.settings, self.clock = db, settings, clock
        self.engine = engine or RiskEngine()
        self.state = RiskState()
        self.lock = threading.RLock()  # guards self.state
        self._replay_history()

    # -- startup -----------------------------------------------------------
    def _replay_history(self) -> None:
        for row in self.db.all("SELECT * FROM login_events ORDER BY id"):
            ev = self._event_from_row(row)
            self.state.record_attempt(ev)
            if row["outcome"] == "success":
                self.state.record_success(ev)

    @staticmethod
    def _event_from_row(row) -> LoginEvent:
        return LoginEvent(
            event_id=row["id"], ts=datetime.fromisoformat(row["ts"]), username=row["username"],
            ip=row["ip"], asn=row["asn"], asn_type=row["asn_type"], country=row["country"],
            city=row["city"], lat=row["lat"], lon=row["lon"], device_id=row["device_id"],
            headless=bool(row["headless"]), password_ok=bool(row["password_ok"]),
        )

    # -- helpers -----------------------------------------------------------
    def _event(self, username: str, ctx: LoginContext, password_ok: bool) -> LoginEvent:
        i = ctx.info
        return LoginEvent(event_id=0, ts=ctx.ts or self.clock(), username=username, ip=ctx.ip,
                          asn=i.asn, asn_type=i.asn_type, country=i.country, city=i.city,
                          lat=i.lat, lon=i.lon, device_id=ctx.device_id, headless=ctx.headless,
                          password_ok=password_ok)

    def _store_event(self, ev: LoginEvent, score: float, reasons: list, decision: str,
                     outcome: str, sim_label: str | None) -> int:
        return self.db.run(
            """INSERT INTO login_events (ts, username, ip, asn, asn_type, country, city, lat, lon,
               device_id, headless, password_ok, score, reasons, decision, outcome, sim_label)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ev.ts.isoformat(), ev.username, ev.ip, ev.asn, ev.asn_type, ev.country, ev.city,
             ev.lat, ev.lon, ev.device_id, int(ev.headless), int(ev.password_ok), score,
             ";".join(f"{n}:{p:+g}" for n, p in reasons), decision, outcome, sim_label))

    def _set_outcome(self, event_id: int, outcome: str) -> None:
        self.db.run("UPDATE login_events SET outcome=? WHERE id=?", (outcome, event_id))

    def _issue_session(self, username: str, device_id: str) -> dict:
        token, now = new_token(), self.clock()
        expires = now + timedelta(hours=self.settings.session_hours)
        self.db.run("INSERT INTO sessions VALUES (?,?,?,?,?)",
                    (token_hash(token), username, device_id, now.isoformat(), expires.isoformat()))
        return {"session_token": token, "expires_at": expires.isoformat() + "Z"}

    def _risk(self, score: float, reasons: list, decision: str) -> dict:
        out = {"score": score, "decision": decision}
        if self.settings.sim_mode:  # never reveal the rules to real clients
            out["reasons"] = [{"rule": n, "points": p} for n, p in reasons]
        return out

    # -- signup --------------------------------------------------------------
    def signup(self, username: str, password: str, ctx: LoginContext) -> dict:
        if not USERNAME_RE.match(username):
            raise AuthError("invalid_username", "Use 3–64 letters, digits or . _ @ -")
        if not 8 <= len(password) <= 128:
            raise AuthError("weak_password", "Use a password of 8 to 128 characters.")
        secret = pyotp.random_base32()
        with self.lock:
            if self.db.one("SELECT 1 FROM users WHERE username=?", (username,)):
                raise AuthError("username_taken", "That username is already registered.", 409)
            self.db.run("INSERT INTO users (username, pw_hash, totp_secret, created_at) VALUES (?,?,?,?)",
                        (username, hash_password(password), secret, self.clock().isoformat()))
            # The signup device and network become the user's first known history.
            ev = self._event(username, ctx, password_ok=True)
            self._store_event(ev, 0.0, [], "signup", "success", ctx.sim_label)
            self.state.record(ev, success=True)
        return {
            "status": "ok",
            "totp_secret": secret,
            "otpauth_uri": pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name=ISSUER),
            **self._issue_session(username, ctx.device_id),
        }

    # -- login ---------------------------------------------------------------
    def login(self, username: str, password: str, ctx: LoginContext) -> dict:
        user = self.db.one("SELECT * FROM users WHERE username=?", (username,))
        pw_ok = verify_password(password, user["pw_hash"] if user else DUMMY_HASH) and user is not None

        with self.lock:
            ev = self._event(username, ctx, pw_ok)
            out = self.engine.evaluate(ev, self.state)
            score, reasons, decision = out["score"], out["reasons"], out["decision"]
            self.state.record_attempt(ev)

            if not pw_ok:
                event_id = self._store_event(ev, score, reasons, decision, "bad_password", ctx.sim_label)
                if decision == STEP_UP:
                    # Decoy challenge: a risky attempt with a wrong password looks the same
                    # as one with a right password, so stuffing bots can't use the
                    # step-up prompt to learn which leaked credentials are valid.
                    return self._open_challenge(event_id, username, score, reasons, decision)
                raise AuthError("denied", "We couldn't sign you in with those details.", 401)

            if decision == BLOCK:
                self._store_event(ev, score, reasons, decision, "blocked", ctx.sim_label)
                # Same message as a wrong password: don't confirm the credentials work.
                raise AuthError("denied", "We couldn't sign you in with those details.", 401)

            if decision == STEP_UP:
                event_id = self._store_event(ev, score, reasons, decision, "pending", ctx.sim_label)
                return self._open_challenge(event_id, username, score, reasons, decision)

            assert decision == ALLOW
            self._store_event(ev, score, reasons, decision, "success", ctx.sim_label)
            self.state.record_success(ev)
        return {"status": "ok", "risk": self._risk(score, reasons, decision),
                **self._issue_session(username, ctx.device_id)}

    def _open_challenge(self, event_id: int, username: str, score, reasons, decision) -> dict:
        cid = secrets.token_urlsafe(16)
        expires = self.clock() + timedelta(minutes=self.settings.challenge_minutes)
        self.db.run("INSERT INTO challenges VALUES (?,?,?,?,?,?)",
                    (cid, event_id, username, expires.isoformat(), self.settings.challenge_attempts, "open"))
        return {"status": "step_up", "method": "totp", "challenge_id": cid,
                "expires_at": expires.isoformat() + "Z", "risk": self._risk(score, reasons, decision)}

    # -- step-up -------------------------------------------------------------
    def verify_step_up(self, challenge_id: str, code: str) -> dict:
        with self.lock:
            ch = self.db.one("SELECT * FROM challenges WHERE id=?", (challenge_id,))
            if ch is None or ch["status"] != "open":
                raise AuthError("challenge_closed", "This sign-in request has ended. Sign in again.", 410)
            now = self.clock()
            if now > datetime.fromisoformat(ch["expires_at"]):
                self.db.run("UPDATE challenges SET status='expired' WHERE id=?", (challenge_id,))
                self._set_outcome(ch["event_id"], "challenge_expired")
                raise AuthError("challenge_expired", "The code request expired. Sign in again.", 410)

            row = self.db.one("SELECT * FROM login_events WHERE id=?", (ch["event_id"],))
            user = self.db.one("SELECT * FROM users WHERE username=?", (ch["username"],))
            ok = bool(row["password_ok"]) and user is not None and self._check_totp(user, code, now)

            if ok:
                self.db.run("UPDATE challenges SET status='passed' WHERE id=?", (challenge_id,))
                self._set_outcome(row["id"], "success")
                self.state.record_success(self._event_from_row(row))  # device is now trusted
                return {"status": "ok", **self._issue_session(row["username"], row["device_id"])}

            left = ch["attempts_left"] - 1
            if left <= 0:
                self.db.run("UPDATE challenges SET status='failed', attempts_left=0 WHERE id=?",
                            (challenge_id,))
                if row["password_ok"]:
                    self._set_outcome(row["id"], "challenge_failed")
                raise AuthError("challenge_failed", "Too many wrong codes. Sign in again.", 410)
            self.db.run("UPDATE challenges SET attempts_left=? WHERE id=?", (left, challenge_id))
            raise AuthError("invalid_code", "That code didn't work.", 401, attempts_left=left)

    def _check_totp(self, user, code: str, now: datetime) -> bool:
        """Accept the current 30s code or one step either side, and never the same step twice."""
        code = (code or "").strip()
        if not re.fullmatch(r"\d{6}", code):
            return False
        totp = pyotp.TOTP(user["totp_secret"])
        aware = now.replace(tzinfo=timezone.utc)
        for offset in (0, -1, 1):
            t = aware + timedelta(seconds=30 * offset)
            if hmac.compare_digest(totp.at(t), code):
                step = totp.timecode(t)
                if step <= user["totp_last_step"]:
                    return False  # replayed code
                self.db.run("UPDATE users SET totp_last_step=? WHERE username=?",
                            (step, user["username"]))
                return True
        return False

    # -- sessions ------------------------------------------------------------
    def session_user(self, token: str) -> dict:
        row = self.db.one("SELECT * FROM sessions WHERE token_hash=?", (token_hash(token),))
        if row is None or self.clock() > datetime.fromisoformat(row["expires_at"]):
            raise AuthError("unauthenticated", "Sign in to continue.", 401)
        return {"username": row["username"], "device_id": row["device_id"],
                "expires_at": row["expires_at"] + "Z"}

    def logout(self, token: str) -> None:
        self.db.run("DELETE FROM sessions WHERE token_hash=?", (token_hash(token),))

    # -- admin ---------------------------------------------------------------
    def recent_events(self, limit: int = 100) -> list[dict]:
        rows = self.db.all("SELECT * FROM login_events ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in rows]
