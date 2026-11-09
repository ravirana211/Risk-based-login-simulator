"""FastAPI app: signup, risk-scored login, TOTP step-up, sessions, admin event log.

Run:  RISKAUTH_SIM_MODE=1 uvicorn api.app:app --reload
Docs: http://localhost:8000/docs
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from typing import Callable

from fastapi import Depends, FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .config import Settings
from .db import Database
from .ipintel import IpInfo, MaxMindIpIntel, StaticIpIntel
from .service import AuthError, AuthService, LoginContext, utcnow


class DeviceIn(BaseModel):
    id: str = Field(min_length=8, max_length=128, description="Stable device fingerprint hash from the client")
    headless: bool = Field(False, description="Client-side automation signal, e.g. navigator.webdriver")


class CredentialsIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
    device: DeviceIn


class StepUpIn(BaseModel):
    challenge_id: str = Field(min_length=8, max_length=64)
    code: str = Field(min_length=1, max_length=10)


class SimContext(BaseModel):
    """Body of the X-Sim-Context header (simulation mode only)."""

    ip: str | None = None
    asn: int = 0
    asn_type: str = "residential"
    country: str = "ZZ"
    city: str = "Unknown"
    lat: float = 0.0
    lon: float = 0.0
    ts: datetime | None = None  # naive UTC
    label: str | None = None  # ground truth, e.g. "attack:impossible_travel"


def create_app(settings: Settings | None = None, ip_intel=None,
               clock: Callable[[], datetime] = utcnow) -> FastAPI:
    settings = settings or Settings.from_env()
    if ip_intel is None:
        ip_intel = (MaxMindIpIntel(settings.geoip_city_db, settings.geoip_asn_db)
                    if settings.geoip_city_db and settings.geoip_asn_db else StaticIpIntel())
    service = AuthService(Database(settings.db_path), settings, clock=clock)

    app = FastAPI(title="Risk-based login API", version="0.1.0")
    app.state.service = service
    if settings.sim_mode:
        app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    @app.exception_handler(AuthError)
    async def _auth_error(_: Request, e: AuthError):
        return JSONResponse({"status": e.code, "message": e.message, **e.extra}, status_code=e.status)

    def context(request: Request, device: DeviceIn,
                x_sim_context: str | None = None) -> LoginContext:
        ip = request.client.host if request.client else "0.0.0.0"
        fwd = request.headers.get("x-forwarded-for")
        if settings.trust_proxy and fwd:
            ip = fwd.split(",")[0].strip()
        if settings.sim_mode and x_sim_context:
            try:
                sim = SimContext(**json.loads(x_sim_context))
            except (ValueError, TypeError) as exc:
                raise AuthError("bad_sim_context", f"X-Sim-Context is not valid: {exc}") from exc
            info = IpInfo(sim.asn, sim.asn_type, sim.country, sim.city, sim.lat, sim.lon)
            return LoginContext(ip=sim.ip or ip, info=info, device_id=device.id,
                                headless=device.headless,
                                ts=sim.ts.replace(tzinfo=None) if sim.ts else None,
                                sim_label=sim.label)
        return LoginContext(ip=ip, info=ip_intel.lookup(ip), device_id=device.id,
                            headless=device.headless)

    def bearer(authorization: str | None = Header(None)) -> str:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise AuthError("unauthenticated", "Sign in to continue.", 401)
        return authorization[7:].strip()

    def admin(x_admin_token: str | None = Header(None)) -> None:
        if settings.sim_mode:
            return
        if not settings.admin_token or x_admin_token != settings.admin_token:
            raise AuthError("forbidden", "Admin access required.", 403)

    @app.get("/health")
    def health():
        return {"status": "ok", "sim_mode": settings.sim_mode}

    @app.post("/signup", status_code=201)
    def signup(body: CredentialsIn, request: Request, x_sim_context: str | None = Header(None)):
        return service.signup(body.username, body.password, context(request, body.device, x_sim_context))

    @app.post("/login")
    def login(body: CredentialsIn, request: Request, x_sim_context: str | None = Header(None)):
        """Returns `status: ok` with a session, `status: step_up` with a challenge, or 401."""
        return service.login(body.username, body.password, context(request, body.device, x_sim_context))

    @app.post("/login/step-up")
    def step_up(body: StepUpIn):
        return service.verify_step_up(body.challenge_id, body.code)

    @app.get("/me")
    def me(token: str = Depends(bearer)):
        return service.session_user(token)

    @app.post("/logout", status_code=204)
    def logout(token: str = Depends(bearer)):
        service.logout(token)

    @app.get("/admin/events", dependencies=[Depends(admin)])
    def events(limit: int = 100):
        return service.recent_events(min(max(limit, 1), 1000))

    @app.get("/admin/policy", dependencies=[Depends(admin)])
    def policy():
        return {"weights": asdict(service.engine.weights), "policy": asdict(service.engine.policy)}

    return app


def __getattr__(name: str):
    # `uvicorn api.app:app` builds the app from the environment when first imported.
    if name == "app":
        global app
        app = create_app()
        return app
    raise AttributeError(name)
