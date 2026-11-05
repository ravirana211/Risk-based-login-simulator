"""Synthetic login traffic: realistic good users plus labelled attack scenarios.

The good-user population includes the edge cases that cause real false
positives (travellers, VPN users, new phones, shift workers, typos). Without
them, every policy looks perfect.
"""
from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .events import LoginEvent, haversine_km

# (city, country, lat, lon, utc_offset_hours)
CITIES = [
    ("New York", "US", 40.71, -74.01, -5),
    ("San Francisco", "US", 37.77, -122.42, -8),
    ("Chicago", "US", 41.88, -87.63, -6),
    ("Toronto", "CA", 43.65, -79.38, -5),
    ("Mexico City", "MX", 19.43, -99.13, -6),
    ("Sao Paulo", "BR", -23.55, -46.63, -3),
    ("London", "GB", 51.51, -0.13, 0),
    ("Amsterdam", "NL", 52.37, 4.90, 1),
    ("Berlin", "DE", 52.52, 13.40, 1),
    ("Paris", "FR", 48.86, 2.35, 1),
    ("Lagos", "NG", 6.52, 3.38, 1),
    ("Moscow", "RU", 55.76, 37.62, 3),
    ("Dubai", "AE", 25.20, 55.27, 4),
    ("Mumbai", "IN", 19.08, 72.88, 5.5),
    ("Bangalore", "IN", 12.97, 77.59, 5.5),
    ("Singapore", "SG", 1.35, 103.82, 8),
    ("Jakarta", "ID", -6.21, 106.85, 7),
    ("Seoul", "KR", 37.57, 126.98, 9),
    ("Tokyo", "JP", 35.68, 139.69, 9),
    ("Sydney", "AU", -33.87, 151.21, 10),
]
COUNTRIES = sorted({c[1] for c in CITIES})
# Real hosting / VPN ASNs (AWS, DigitalOcean, Hetzner, OVH, Linode, M247)
HOSTING_ASNS = [16509, 14061, 24940, 16276, 63949, 9009]
VPN_EXIT_CITIES = [c for c in CITIES if c[1] in ("US", "NL", "GB", "DE", "SG")]


def residential_asns(country: str) -> list[int]:
    base = 60000 + COUNTRIES.index(country) * 10
    return [base + i for i in range(4)]


def mobile_asn(country: str) -> int:
    return 60000 + COUNTRIES.index(country) * 10 + 9


@dataclass
class SimConfig:
    n_users: int = 2000
    days: int = 30
    warmup_days: int = 7  # build history; excluded from metrics, no attacks
    seed: int = 42
    start: datetime = datetime(2026, 10, 1)
    # good-user personas (share of users)
    p_traveler: float = 0.06
    p_vpn: float = 0.07
    p_new_phone: float = 0.12
    p_shift_worker: float = 0.08
    p_typo: float = 0.06  # per login
    # attack volume
    stuffing_campaigns: int = 6
    smart_stuffing_campaigns: int = 4
    brute_force_targets: int = 10
    impossible_travel_victims: int = 40
    new_device_3am_victims: int = 40
    local_attacker_victims: int = 30
    stuffing_success: float = 0.03  # share of leaked creds that still work


@dataclass
class User:
    username: str
    city: tuple
    home_asn: int
    devices: list[str]
    hour_mean: float  # local time
    hour_sd: float
    rate: float  # logins per day
    traveler: bool = False
    vpn: bool = False
    new_phone_day: int | None = None
    new_phone_id: str | None = None
    shift_worker: bool = False
    trip: tuple[int, int, tuple] | None = None  # (start_day, end_day, city)
    timeline: list[LoginEvent] = field(default_factory=list)


class Generator:
    def __init__(self, cfg: SimConfig | None = None):
        self.cfg = cfg or SimConfig()
        self.rng = random.Random(self.cfg.seed)
        self.events: list[LoginEvent] = []
        self.users: list[User] = []

    # -- helpers -----------------------------------------------------------
    def _ip(self) -> str:
        r = self.rng
        return f"{r.randint(11, 223)}.{r.randint(0, 255)}.{r.randint(0, 255)}.{r.randint(1, 254)}"

    def _device(self) -> str:
        return "dev-" + uuid.UUID(int=self.rng.getrandbits(128)).hex[:12]

    def _emit(self, **kw) -> LoginEvent:
        ts = kw["ts"]
        kw.setdefault("warmup", ts < self.cfg.start + timedelta(days=self.cfg.warmup_days))
        city = kw.pop("city_t")
        ev = LoginEvent(event_id=0, city=city[0], country=city[1], lat=city[2], lon=city[3], **kw)
        self.events.append(ev)
        return ev

    def _local_to_utc(self, day: int, local_hour: float, city: tuple) -> datetime:
        local_hour %= 24
        return self.cfg.start + timedelta(days=day, hours=local_hour - city[4])

    def _attack_day(self) -> int:
        # +1 day so timezone shifts never push an attack back into warm-up
        return self.rng.randint(self.cfg.warmup_days + 1, self.cfg.days - 1)

    # -- good users ----------------------------------------------------------
    def make_users(self) -> None:
        r, cfg = self.rng, self.cfg
        for i in range(cfg.n_users):
            city = r.choice(CITIES)
            u = User(
                username=f"user{i:05d}",
                city=city,
                home_asn=r.choice(residential_asns(city[1])),
                devices=[self._device() for _ in range(r.choice([1, 1, 2, 2, 3]))],
                hour_mean=min(max(r.gauss(13, 3.5), 6), 23),
                hour_sd=r.uniform(1.0, 2.5),
                rate=r.uniform(0.3, 2.0),
            )
            if r.random() < cfg.p_shift_worker:
                u.shift_worker, u.hour_mean = True, r.uniform(0.5, 4.5)
            u.vpn = r.random() < cfg.p_vpn
            if r.random() < cfg.p_new_phone:
                u.new_phone_day = r.randint(cfg.warmup_days, cfg.days - 1)
                u.new_phone_id = self._device()
            if r.random() < cfg.p_traveler:
                u.traveler = True
                start = r.randint(cfg.warmup_days, max(cfg.warmup_days, cfg.days - 6))
                dest = r.choice([c for c in CITIES if c[1] != city[1]])
                u.trip = (start, start + r.randint(3, 6), dest)
            self.users.append(u)

    def simulate_good(self) -> None:
        r, cfg = self.rng, self.cfg
        for u in self.users:
            for day in range(cfg.days):
                if u.trip and day == u.trip[0]:
                    continue  # travel day: on a plane, no logins
                for _ in range(self._poisson(u.rate)):
                    self._good_login(u, day)

    def _poisson(self, lam: float) -> int:
        l, k, p = math.exp(-lam), 0, 1.0
        while True:
            p *= self.rng.random()
            if p < l:
                return k
            k += 1

    def _good_login(self, u: User, day: int) -> None:
        r = self.rng
        scenario = "shift_worker" if u.shift_worker else "normal"
        loc, asn, asn_type = u.city, u.home_asn, "residential"

        devices = list(u.devices)
        on_new_phone = u.new_phone_day is not None and day >= u.new_phone_day
        if on_new_phone:
            devices[0] = u.new_phone_id  # primary phone replaced
        device = devices[0] if r.random() < 0.75 else r.choice(devices)
        if on_new_phone and device == devices[0]:
            scenario = "new_phone"
        elif device != devices[0] and scenario == "normal":
            scenario = "secondary_device"

        if r.random() < 0.3:  # on mobile data
            asn, asn_type = mobile_asn(loc[1]), "mobile"

        if u.trip and u.trip[0] < day <= u.trip[1]:
            loc = u.trip[2]
            asn, asn_type, scenario = r.choice(residential_asns(loc[1])), "residential", "travel"
        elif u.vpn and r.random() < 0.4:
            loc = r.choice(VPN_EXIT_CITIES)
            asn, asn_type, scenario = r.choice(HOSTING_ASNS[:2] + HOSTING_ASNS[-1:]), "hosting", "vpn"

        local_hour = r.gauss(u.hour_mean, u.hour_sd)
        ts = self._local_to_utc(day, local_hour, loc) + timedelta(seconds=r.randint(0, 59))
        ip = self._ip()
        common = dict(username=u.username, ip=ip, asn=asn, asn_type=asn_type, city_t=loc,
                      device_id=device, headless=False, label="good")
        if r.random() < self.cfg.p_typo:
            self._emit(ts=ts - timedelta(seconds=r.randint(8, 40)), password_ok=False,
                       scenario="typo", **common)
        self._emit(ts=ts, password_ok=True, scenario=scenario, **common)

    # -- attacks -------------------------------------------------------------
    def _victim(self) -> User:
        return self.rng.choice(self.users)

    def _victim_login_after_warmup(self) -> tuple[User, LoginEvent] | None:
        cutoff = self.cfg.start + timedelta(days=self.cfg.warmup_days)
        for _ in range(50):
            u = self._victim()
            mine = [e for e in self.events if e.username == u.username and e.label == "good"
                    and e.password_ok and e.ts >= cutoff]
            if mine:
                return u, self.rng.choice(mine)
        return None

    def simulate_attacks(self) -> None:
        r, cfg = self.rng, self.cfg
        users = self.users

        # 1. Credential stuffing from datacenter/Tor IPs with bots
        for _ in range(cfg.stuffing_campaigns):
            t = self.cfg.start + timedelta(days=self._attack_day(), hours=r.uniform(0, 24))
            for _ in range(8):
                city = r.choice(CITIES)
                tor = r.random() < 0.15
                ip, asn = self._ip(), r.choice(HOSTING_ASNS)
                headless = r.random() < 0.7
                bot_dev = self._device()
                ts = t + timedelta(minutes=r.uniform(0, 30))
                for v in r.sample(users, min(len(users), r.randint(25, 60))):
                    ts += timedelta(seconds=r.uniform(5, 40))
                    self._emit(ts=ts, username=v.username, ip=ip, asn=asn,
                               asn_type="tor" if tor else "hosting", city_t=city,
                               device_id=bot_dev if r.random() < 0.5 else self._device(),
                               headless=headless, password_ok=r.random() < cfg.stuffing_success,
                               label="attack", scenario="credential_stuffing")

        # 2. "Smart" stuffing through rotating residential proxies, real browsers
        for _ in range(cfg.smart_stuffing_campaigns):
            ts = self.cfg.start + timedelta(days=self._attack_day(), hours=r.uniform(0, 24))
            for v in r.sample(users, min(len(users), 150)):
                ts += timedelta(seconds=r.uniform(20, 120))
                city = r.choice(CITIES)
                self._emit(ts=ts, username=v.username, ip=self._ip(),
                           asn=r.choice(residential_asns(city[1])), asn_type="residential",
                           city_t=city, device_id=self._device(), headless=False,
                           password_ok=r.random() < cfg.stuffing_success,
                           label="attack", scenario="smart_stuffing")

        # 3. Brute force: one account, many passwords, one IP
        for _ in range(cfg.brute_force_targets):
            v, city = self._victim(), r.choice(CITIES)
            ip, asn = self._ip(), r.choice(HOSTING_ASNS)
            dev = self._device()
            ts = self.cfg.start + timedelta(days=self._attack_day(), hours=r.uniform(0, 24))
            n = r.randint(15, 40)
            for k in range(n):
                ts += timedelta(seconds=r.uniform(3, 20))
                ok = k == n - 1 and r.random() < 0.3
                self._emit(ts=ts, username=v.username, ip=ip, asn=asn, asn_type="hosting",
                           city_t=city, device_id=dev, headless=True, password_ok=ok,
                           label="attack", scenario="brute_force")

        # 4. Impossible travel: valid creds used far away shortly after the real user
        for _ in range(cfg.impossible_travel_victims):
            pick = self._victim_login_after_warmup()
            if not pick:
                continue
            u, legit = pick
            far = [c for c in CITIES if haversine_km(c[2], c[3], legit.lat, legit.lon) > 3000]
            city = r.choice(far)
            hosting = r.random() < 0.4
            self._emit(ts=legit.ts + timedelta(minutes=r.uniform(15, 180)), username=u.username,
                       ip=self._ip(), asn=r.choice(HOSTING_ASNS) if hosting else r.choice(residential_asns(city[1])),
                       asn_type="hosting" if hosting else "residential", city_t=city,
                       device_id=self._device(), headless=False, password_ok=True,
                       label="attack", scenario="impossible_travel")

        # 5. New device at 3am (victim's local time), same country
        for _ in range(cfg.new_device_3am_victims):
            u = self._victim()
            city = r.choice([c for c in CITIES if c[1] == u.city[1]])
            ts = self._local_to_utc(self._attack_day(), r.uniform(1, 5), u.city)
            self._emit(ts=ts, username=u.username, ip=self._ip(),
                       asn=r.choice(residential_asns(city[1])), asn_type="residential",
                       city_t=city, device_id=self._device(), headless=False, password_ok=True,
                       label="attack", scenario="new_device_3am")

        # 6. Local attacker: residential proxy in the victim's city at normal hours (hard)
        for _ in range(cfg.local_attacker_victims):
            u = self._victim()
            ts = self._local_to_utc(self._attack_day(), r.gauss(u.hour_mean, u.hour_sd), u.city)
            self._emit(ts=ts, username=u.username, ip=self._ip(),
                       asn=r.choice(residential_asns(u.city[1])), asn_type="residential",
                       city_t=u.city, device_id=self._device(), headless=False, password_ok=True,
                       label="attack", scenario="local_attacker")

    def run(self) -> list[LoginEvent]:
        self.make_users()
        self.simulate_good()
        self.simulate_attacks()
        self.events.sort(key=lambda e: e.ts)
        for i, e in enumerate(self.events):
            e.event_id = i
        return self.events


def generate(cfg: SimConfig | None = None) -> list[LoginEvent]:
    return Generator(cfg).run()
