"""
하남시 보건소 조직도 크롤링 → src/data/contacts.json

실행:
    python scripts/crawl_contacts.py
"""
import json
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://www.hanam.go.kr/health/selectEmplHealthCtrWebList.do?key=891"
OUT_PATH = Path(__file__).parent.parent / "src" / "data" / "contacts.json"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def parse_contacts(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")
    if not tables:
        return []

    contacts = []
    current_team = ""

    for table in tables:
        for tr in table.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue

            # 팀명: 비어있으면 이전 팀 이어받기
            team_text = tds[0].get_text(strip=True)
            if team_text:
                current_team = team_text

            role = tds[1].get_text(strip=True)
            phone_tag = tds[2].find("a")
            phone = phone_tag.get_text(strip=True) if phone_tag else tds[2].get_text(strip=True)

            # 담당업무: 첫 줄만 (핵심 업무)
            duty_td = tds[3] if len(tds) > 3 else None
            duties = ""
            if duty_td:
                lines = [line.strip() for line in duty_td.get_text(separator="\n").splitlines() if line.strip()]
                duties = lines[0] if lines else ""

            if phone:
                contacts.append({
                    "team": current_team,
                    "role": role,
                    "phone": phone,
                    "main_duty": duties,
                })

    return contacts


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    resp = requests.get(URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    contacts = parse_contacts(resp.text)

    # 팀별로 그룹화 (팀명 + 대표 전화번호만)
    teams: dict[str, dict] = {}
    for c in contacts:
        team = c["team"]
        if team not in teams:
            teams[team] = {"team": team, "phone": c["phone"], "members": []}
        teams[team]["members"].append({
            "role": c["role"],
            "phone": c["phone"],
            "main_duty": c["main_duty"],
        })

    result = list(teams.values())

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ {len(result)}개 팀/부서 저장: {OUT_PATH}")
    for t in result:
        print(f"  {t['team']} — {t['phone']} ({len(t['members'])}명)")


if __name__ == "__main__":
    main()
