"""
보건소 정책 페이지 크롤링 → src/data/policies/ 마크다운 파일 생성

실행:
    python scripts/crawl_policies.py
"""
import os
import sys
import json
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

POLICIES_DIR = Path(__file__).parent.parent / "src" / "data" / "policies"
POLICIES_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# 정책별 크롤링 URL 목록
POLICY_SOURCES = {
    "암의료비지원": [
        "https://www.hanam.go.kr/health/contents.do?key=974",
    ],
    "희귀질환의료비지원": [
        "https://www.hanam.go.kr/health/contents.do?key=975",
        "https://helpline.kdca.go.kr/cdchelp/ph/ptlcontents/selectPtlConSent.do?schSno=111&menu=B0101",
        "https://helpline.kdca.go.kr/cdchelp/ph/ptlcontents/selectPtlConSent.do?schSno=112&menu=B0101",
        "https://helpline.kdca.go.kr/cdchelp/ph/ptlcontents/selectPtlConSent.do?schSno=113&menu=B0101",
        "https://helpline.kdca.go.kr/cdchelp/ph/ptlcontents/selectPtlConSent.do?schSno=114&menu=B0101",
        "https://helpline.kdca.go.kr/cdchelp/ph/ptlcontents/selectPtlConSent.do?schSno=115&menu=B0101",
        "https://helpline.kdca.go.kr/cdchelp/ph/ptlcontents/selectPtlConSent.do?schSno=116&menu=B0101",
        "https://helpline.kdca.go.kr/cdchelp/ph/ptlcontents/selectPtlConSent.do?schSno=168&menu=B0101",
    ],
    "국가암검진": [
        "https://www.hanam.go.kr/health/contents.do?key=932",
    ],
}

SYSTEM_PROMPT = """당신은 보건소 정책 문서 작성 전문가입니다.
크롤링된 HTML 텍스트를 받아 아래 형식의 마크다운 파일로 변환하세요.

출력 형식 예시 (policy_name이 "산정특례"인 경우):
---
policy_name: 산정특례
eligibility:
  disease_categories: [암, 심장질환, 뇌혈관질환]
  income_threshold: null
  insurance_required: true
  disability_grade: null
support_content: "중증질환자 본인부담률 5%로 경감"
legal_basis: "국민건강보험법 제44조"
article_numbers: ["제44조", "시행령 제19조"]
how_to_apply: "요양기관 또는 건강보험공단 지사 신청"
---

# 산정특례 (중증질환 의료비 경감)

## 지원 대상
...

규칙:
1. policy_name은 반드시 "{policy_name}"으로 기재하세요
2. 제목 형식은 "# {policy_name} (한 줄 부제목)" — 부제목은 정책 내용에 맞게 직접 작성하세요
3. article_numbers는 문서에 실제로 등장한 조항 번호만 기재하세요. 없으면 []로 두세요
4. 원문 내용을 최대한 유지하고, 없는 내용은 추가하지 마세요
5. 마크다운 코드블록(```) 없이 순수 마크다운만 출력하세요"""


def fetch_text(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def structure_with_llm(policy_name: str, raw_text: str) -> str:
    client = OpenAI()
    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "gpt-4o"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(policy_name=policy_name)},
            {"role": "user", "content": f"다음 텍스트를 {policy_name} 정책 문서로 변환하세요:\n\n{raw_text[:20000]}"},
        ],
        temperature=0,
    )
    return response.choices[0].message.content.strip()


def crawl_policy(policy_name: str, urls: list[str]) -> None:
    print(f"\n[{policy_name}] 크롤링 시작 ({len(urls)}개 페이지)")

    texts = []
    for url in urls:
        print(f"  → {url}")
        try:
            text = fetch_text(url)
            texts.append(f"=== {url} ===\n{text}")
            time.sleep(0.5)
        except Exception as e:
            print(f"  ❌ 실패: {e}")

    if not texts:
        print(f"  ❌ [{policy_name}] 수집된 텍스트 없음, 건너뜀")
        return

    combined = "\n\n".join(texts)
    print(f"  → LLM으로 구조화 중...")
    content = structure_with_llm(policy_name, combined)

    out_path = POLICIES_DIR / f"{policy_name}.md"
    out_path.write_text(content, encoding="utf-8")
    print(f"  ✅ 저장: {out_path}")


def main():
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY 환경변수 없음")
        sys.exit(1)

    for policy_name, urls in POLICY_SOURCES.items():
        crawl_policy(policy_name, urls)

    print(f"\n완료: {len(POLICY_SOURCES)}개 정책 문서 생성")


if __name__ == "__main__":
    main()
