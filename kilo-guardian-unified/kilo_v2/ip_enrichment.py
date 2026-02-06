"""IP Enrichment Utility

Provides passive (local) and optional provider-based enrichment for source IPs.
Designed to be lightweight and fail-safe: all exceptions are caught and a minimal
stub structure is returned so security logging never breaks.

Enrichment fields (when available):
- ip: original IP
- is_private: bool
- hostname: reverse DNS if resolvable
- geo: { country, region, city, lat, lon }
- asn: { number, name }
- provider: which provider supplied data (stub/ipinfo/ipdata/ipapi)

External provider calls are only made when ENABLE_IP_ENRICHMENT is true AND a valid
API key is present for the configured provider.
"""

from __future__ import annotations

import json
import logging
import os
import socket
from typing import Dict

try:
    from . import config
except Exception:
    import config  # type: ignore

logger = logging.getLogger("IpEnrichment")

PRIVATE_PREFIXES = [
    "10.",
    "127.",
    "192.168.",
    "172.16.",
    "172.17.",
    "172.18.",
    "172.19.",
    "172.20.",
    "172.21.",
    "172.22.",
    "172.23.",
    "172.24.",
    "172.25.",
    "172.26.",
    "172.27.",
    "172.28.",
    "172.29.",
    "172.30.",
    "172.31.",
    "169.254.",
]

# Simple provider URL mapping
PROVIDER_ENDPOINTS = {
    "ipinfo": "https://ipinfo.io/{ip}/json",
    "ipdata": "https://api.ipdata.co/{ip}?api-key={key}",
    "ipapi": "https://ipapi.co/{ip}/json/",
}

USER_AGENT = "KiloGuardian-IP-Enrichment/1.0"


def _is_private(ip: str) -> bool:
    return any(ip.startswith(pref) for pref in PRIVATE_PREFIXES)


def _reverse_dns(ip: str) -> str | None:
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return None


def _provider_request(ip: str) -> Dict:
    provider = config.IP_ENRICHMENT_PROVIDER
    key = config.IP_ENRICHMENT_API_KEY
    if (
        provider == "stub" or not key and provider != "ipapi"
    ):  # ipapi may work without key but rate limited
        return {}
    import urllib.error
    import urllib.request

    try:
        if provider not in PROVIDER_ENDPOINTS:
            return {}
        url = PROVIDER_ENDPOINTS[provider].format(ip=ip, key=key)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = resp.read().decode("utf-8", "ignore")
            return json.loads(data)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        logger.debug(f"Provider enrichment failed for {ip}: {e}")
        return {}
    except Exception as e:  # blanket catch to avoid breaking security monitor
        logger.debug(f"Unexpected provider error for {ip}: {e}")
        return {}


def enrich_ip(ip: str) -> Dict:
    """Return enrichment details for an IP. Never raises.

    If enrichment disabled in config, returns minimal stub with disabled flag.
    """
    base = {
        "ip": ip,
        "enabled": bool(getattr(config, "ENABLE_IP_ENRICHMENT", False)),
        "provider": config.IP_ENRICHMENT_PROVIDER,
        "is_private": _is_private(ip),
        "hostname": None,
        "geo": {},
        "asn": {},
    }
    if not base["enabled"]:
        return base
    # Reverse DNS first (quick passive)
    base["hostname"] = _reverse_dns(ip)
    # External provider if configured
    provider_data = _provider_request(ip)
    try:
        if provider_data:
            # Attempt mapping for common schemas
            # ipinfo: { ip, city, region, country, loc, org }
            if config.IP_ENRICHMENT_PROVIDER == "ipinfo":
                loc = provider_data.get("loc", ",")
                lat, lon = (loc.split(",") + [None])[:2]
                base["geo"] = {
                    "city": provider_data.get("city"),
                    "region": provider_data.get("region"),
                    "country": provider_data.get("country"),
                    "lat": lat,
                    "lon": lon,
                }
                org = provider_data.get("org", "")
                if org:
                    parts = org.split(" ", 1)
                    if parts:
                        base["asn"] = {
                            "number": parts[0],
                            "name": parts[1] if len(parts) > 1 else None,
                        }
            elif config.IP_ENRICHMENT_PROVIDER == "ipdata":
                base["geo"] = {
                    "city": provider_data.get("city"),
                    "region": provider_data.get("region"),
                    "country": provider_data.get("country_name"),
                    "lat": provider_data.get("latitude"),
                    "lon": provider_data.get("longitude"),
                }
                asn = provider_data.get("asn", {})
                base["asn"] = {"number": asn.get("asn"), "name": asn.get("name")}
            elif config.IP_ENRICHMENT_PROVIDER == "ipapi":
                base["geo"] = {
                    "city": provider_data.get("city"),
                    "region": provider_data.get("region"),
                    "country": provider_data.get("country_name"),
                    "lat": provider_data.get("latitude"),
                    "lon": provider_data.get("longitude"),
                }
                base["asn"] = {
                    "number": provider_data.get("asn"),
                    "name": provider_data.get("org"),
                }
    except Exception as e:
        logger.debug(f"Mapping provider data failed for {ip}: {e}")
    return base


__all__ = ["enrich_ip"]
