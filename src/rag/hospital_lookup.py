"""Find nearest cancer screening hospitals given a district name and cancer type."""

import json
import math
import os
import requests
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

HOSPITALS_PATH = Path(__file__).parent.parent / "data" / "hospitals.json"
NAVER_CLIENT_ID = os.getenv("NAVER_MAP_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_MAP_CLIENT_SECRET")


@lru_cache(maxsize=1)
def _load_hospitals() -> list[dict]:
    return json.loads(HOSPITALS_PATH.read_text(encoding="utf-8"))


def _geocode_address(address: str) -> tuple[float, float] | None:
    url = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
        "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET,
    }
    res = requests.get(url, params={"query": address}, headers=headers, timeout=5)
    data = res.json()
    if data.get("status") == "OK" and data.get("addresses"):
        addr = data["addresses"][0]
        return float(addr["y"]), float(addr["x"])
    return None


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Returns distance in km."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def find_nearest(address: str, cancer_type: str | None = None, top_n: int = 5) -> list[dict]:
    """
    Returns nearest hospitals for the given address and optional cancer type.
    Falls back to all hospitals if geocoding fails.
    """
    hospitals = _load_hospitals()

    if cancer_type:
        hospitals = [h for h in hospitals if cancer_type in h.get("cancers", [])]

    coords = _geocode_address(address)
    if not coords:
        # Can't geocode — return hospitals that have coordinates, sorted by name
        result = [h for h in hospitals if h.get("lat")][:top_n]
        for h in result:
            h = h.copy()
        return [_format(h, None) for h in result]

    origin_lat, origin_lng = coords
    with_dist = []
    for h in hospitals:
        if h.get("lat") and h.get("lng"):
            dist = _haversine(origin_lat, origin_lng, h["lat"], h["lng"])
            with_dist.append((dist, h))

    with_dist.sort(key=lambda x: x[0])
    return [_format(h, dist) for dist, h in with_dist[:top_n]]


def _format(hospital: dict, distance_km: float | None) -> dict:
    result = {
        "name": hospital["name"],
        "phone": hospital["phone"],
        "cancers": hospital.get("cancers", []),
    }
    if distance_km is not None:
        result["distance_km"] = round(distance_km, 2)
    return result
