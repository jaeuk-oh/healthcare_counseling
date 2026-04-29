import csv
import re
from functools import lru_cache
from pathlib import Path

CSV_PATH = Path(__file__).parent.parent / "data" / "rare_diseases.csv"


def _simplify(name: str) -> str:
    """괄호 및 괄호 내용 제거 후 공백 정리."""
    return re.sub(r"\s*\(.*?\)\s*", "", name).strip()


@lru_cache(maxsize=1)
def _load_diseases() -> list[dict]:
    with open(CSV_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    # 단순화 이름 미리 계산
    for row in rows:
        row["_simple_name"] = _simplify(row["korean_name"])
    return rows


def lookup(query: str) -> list[dict]:
    """병명(괄호 제거 포함) 또는 KCD 코드로 희귀질환 여부 조회."""
    diseases = _load_diseases()
    seen = set()
    matches = []

    for row in diseases:
        name = row["korean_name"]
        simple = row["_simple_name"]
        kcd = row["kcd_code"]

        hit = (
            (name and name in query)
            or (simple and simple in query)
            or (kcd and kcd in query)
        )

        if hit and name not in seen:
            seen.add(name)
            matches.append({
                "korean_name": name,
                "kcd_code": kcd,
            })

    return matches
