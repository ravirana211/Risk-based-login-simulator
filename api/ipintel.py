"""IP → ASN, ASN type and location.

Two providers:
- `StaticIpIntel`: no external data. Private/loopback IPs map to a configurable
  "home" location; everything else is unknown. Good for local development.
- `MaxMindIpIntel`: reads GeoLite2-City and GeoLite2-ASN .mmdb files
  (free with a MaxMind account; `pip install maxminddb`).

Both classify well-known hosting/VPN ASNs as "hosting". A real deployment
would add a commercial IP-reputation feed and the Tor exit list.
"""
from __future__ import annotations

import ipaddress
from dataclasses import dataclass

from risksim.generator import HOSTING_ASNS

# Common cloud / VPN ASNs. Extend from your own data.
HOSTING = set(HOSTING_ASNS) | {
    8075,  # Microsoft
    15169, 396982,  # Google
    13335,  # Cloudflare
    20473,  # Vultr
    212238, 60068,  # Datacamp / CDN77 (common VPN exits)
}


@dataclass
class IpInfo:
    asn: int
    asn_type: str
    country: str
    city: str
    lat: float
    lon: float


class StaticIpIntel:
    def __init__(self, home: IpInfo | None = None):
        self.home = home or IpInfo(asn=64512, asn_type="residential", country="ZZ",
                                   city="Local", lat=0.0, lon=0.0)

    def lookup(self, ip: str) -> IpInfo:
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return IpInfo(0, "residential", "ZZ", "Unknown", 0.0, 0.0)
        if addr.is_private or addr.is_loopback:
            return self.home
        return IpInfo(0, "residential", "ZZ", "Unknown", 0.0, 0.0)


class MaxMindIpIntel:
    def __init__(self, city_db: str, asn_db: str):
        import maxminddb  # optional dependency

        self.city = maxminddb.open_database(city_db)
        self.asn = maxminddb.open_database(asn_db)

    def lookup(self, ip: str) -> IpInfo:
        c = self.city.get(ip) or {}
        a = self.asn.get(ip) or {}
        asn = int(a.get("autonomous_system_number") or 0)
        loc = c.get("location") or {}
        return IpInfo(
            asn=asn,
            asn_type="hosting" if asn in HOSTING else "residential",
            country=(c.get("country") or {}).get("iso_code") or "ZZ",
            city=((c.get("city") or {}).get("names") or {}).get("en") or "Unknown",
            lat=float(loc.get("latitude") or 0.0),
            lon=float(loc.get("longitude") or 0.0),
        )
