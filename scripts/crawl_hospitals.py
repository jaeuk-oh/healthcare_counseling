"""Crawl cancer screening hospitals from hanam.go.kr, find addresses via Naver search, geocode via Naver Maps API."""

import json
import os
import re
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

URL = "https://www.hanam.go.kr/health/contents.do?key=932"
OUT_PATH = Path(__file__).parent.parent / "src" / "data" / "hospitals.json"

NAVER_CLIENT_ID = os.getenv("NAVER_MAP_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_MAP_CLIENT_SECRET")

CANCER_TYPES = ["위암", "간암", "대장암", "유방암", "자궁경부암"]


def crawl_hospitals() -> list[dict]:
    res = requests.get(URL, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "lxml")
    tables = soup.find_all("table")
    hospital_table = tables[1]

    hospitals = []
    for row in hospital_table.find_all("tr")[2:]:
        cells = [td.get_text(strip=True) for td in row.find_all(["th", "td"])]
        if len(cells) < 7:
            continue
        name, phone = cells[0], cells[1]
        if not name:
            continue
        cancers = [CANCER_TYPES[i] for i, c in enumerate(cells[2:7]) if c == "●"]
        hospitals.append({"name": name, "phone": phone, "cancers": cancers})

    print(f"Crawled {len(hospitals)} hospitals")
    return hospitals


def get_address_from_naver(hospital_name: str) -> str | None:
    query = f"{hospital_name} 하남시"
    res = requests.get(
        "https://search.naver.com/search.naver",
        params={"where": "nexearch", "query": query},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=5,
    )
    matches = re.findall(r'경기[^<"]{5,50}[로길동][\s\d-]*', res.text)
    if matches:
        return matches[0].strip()
    return None


def geocode(address: str) -> tuple[float, float] | None:
    res = requests.get(
        "https://maps.apigw.ntruss.com/map-geocode/v2/geocode",
        params={"query": address},
        headers={
            "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
            "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET,
        },
        timeout=5,
    )
    data = res.json()
    if data.get("status") == "OK" and data.get("addresses"):
        addr = data["addresses"][0]
        return float(addr["y"]), float(addr["x"])
    return None


def main():
    hospitals = crawl_hospitals()

    print("Finding addresses and geocoding...")
    for i, h in enumerate(hospitals):
        address = get_address_from_naver(h["name"])
        h["address"] = address

        if address:
            coords = geocode(address)
            if coords:
                h["lat"], h["lng"] = coords
                print(f"  [{i+1}/{len(hospitals)}] {h['name']} → {address} → {coords}")
            else:
                h["lat"] = h["lng"] = None
                print(f"  [{i+1}/{len(hospitals)}] {h['name']} → {address} → 좌표 없음")
        else:
            h["lat"] = h["lng"] = None
            print(f"  [{i+1}/{len(hospitals)}] {h['name']} → 주소 없음")

        time.sleep(0.3)

    OUT_PATH.write_text(json.dumps(hospitals, ensure_ascii=False, indent=2), encoding="utf-8")
    found = sum(1 for h in hospitals if h["lat"])
    print(f"\nSaved {len(hospitals)} hospitals ({found} geocoded) → {OUT_PATH}")


if __name__ == "__main__":
    main()
