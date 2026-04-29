"""
희귀질환 지원 대상 질환 코드 크롤링 (142페이지, 1,413개)
→ src/data/rare_diseases.csv

실행:
    python scripts/crawl_rare_diseases.py
"""
import csv
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = (
    "https://helpline.kdca.go.kr/cdchelp/ph/supbiz/selectMdepSupList.do"
    "?menu=B0102&pageIndex={page}&schGubun=tit&schSuplDcd=&schText="
)
TOTAL_PAGES = 142
OUT_PATH = Path(__file__).parent.parent / "src" / "data" / "rare_diseases.csv"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def parse_page(html: str) -> list[dict]:
    """
    구조: <tr> <th>번호</th> <td><dl>
            <dt>국문명<p>영문명</p></dt>
            <dd><ul>
              <li><span>KCD코드 :</span> Q82.4</li>
              <li><span>산정특례코드 :</span> V900</li>
            </ul></dd>
          </dl></td> </tr>
    """
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        return []

    rows = []
    for tr in table.find_all("tr"):
        td = tr.find("td")
        if not td:
            continue

        dt = td.find("dt")
        if not dt:
            continue

        # 국문명: dt 직접 텍스트 (p 태그 제외)
        p_tag = dt.find("p")
        english_name = p_tag.get_text(strip=True) if p_tag else ""
        if p_tag:
            p_tag.extract()
        korean_name = dt.get_text(strip=True)

        # KCD코드, 산정특례코드: li > span 다음 텍스트
        kcd_code = ""
        spe_code = ""
        for li in td.find_all("li"):
            span = li.find("span")
            if not span:
                continue
            label = span.get_text(strip=True)
            value = li.get_text(strip=True).replace(label, "").strip()
            if "KCD" in label:
                kcd_code = value if value != "없음" else ""
            elif "산정특례" in label:
                spe_code = value

        if korean_name:
            rows.append({
                "korean_name": korean_name,
                "english_name": english_name,
                "kcd_code": kcd_code,
                "special_code": spe_code,
            })

    return rows


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    all_rows = []

    for page in range(1, TOTAL_PAGES + 1):
        url = BASE_URL.format(page=page)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            rows = parse_page(resp.text)
            all_rows.extend(rows)
            print(f"\r  진행: {page}/{TOTAL_PAGES}페이지 ({len(all_rows)}개 수집)", end="", flush=True)
            time.sleep(0.3)
        except Exception as e:
            print(f"\n  ❌ 페이지 {page} 실패: {e}")

    print(f"\n\n총 {len(all_rows)}개 질환 수집 완료")

    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["korean_name", "english_name", "kcd_code", "special_code"])
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"✅ 저장: {OUT_PATH}")


if __name__ == "__main__":
    main()
