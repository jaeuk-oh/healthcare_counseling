"""멀티턴 counselor eval — /chat 루프 + gpt-4o-mini 시민 시뮬레이터."""
import os
import sys
import yaml
import httpx
import requests
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_oai = OpenAI(http_client=httpx.Client())

API_URL = "http://localhost:8000"
SCENARIOS_FILE = Path(__file__).parent.parent / "src" / "data" / "personas.yaml"
MAX_TURNS = 10

TERMINATION_SIGNALS = {
    "방문안내": [
        "내방", "방문하셔서", "내방하시면", "지참하신 후",
        "보건소에 신청하시면", "보건소를 방문", "관할 보건소",
        "보건소에 방문",
    ],
    "지원불가안내": [
        "해당되지 않습니다", "지원 불가", "지원이 어려",
        "해당이 되지 않", "지원받으시기 어려",
        "받으실 수 없", "지원을 받으실 수 없", "신청하실 수 없",
        "불가능합니다", "해당하지 않으시는", "해당하지 않습니다",
        "지원이 안 됩니다", "해당되지 않으십니다",
        "대상이 아닙니다", "에 해당하지 않", "아닙니다",
        "아니에요", "아니세요", "대상이 아니", "대상은 아니",
    ],
}


def detect_termination(message: str) -> str | None:
    for term_type, keywords in TERMINATION_SIGNALS.items():
        if any(kw in message for kw in keywords):
            return term_type
    return None


def simulate_citizen(citizen_profile: str, counselor_message: str) -> str:
    response = _oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": citizen_profile},
            {"role": "user", "content": counselor_message},
        ],
        max_tokens=150,
    )
    return response.choices[0].message.content.strip()


def find_checklist_item(checklist: list[dict], policy: str, label: str) -> dict | None:
    for item in checklist:
        if item["name"] == policy:
            for c in item["criteria"]:
                if c["label"] == label:
                    return c
    return None


def evaluate_scenario(scenario: dict, final_checklist: list[dict], termination_type: str | None, turns: int = 0) -> dict:
    result = {"id": scenario["id"], "passed": True, "failures": []}

    # 종료 유형 검증
    expected_term = scenario["expected_termination"]
    if termination_type != expected_term:
        result["passed"] = False
        result["failures"].append(
            f"종료유형 불일치: expected={expected_term}, actual={termination_type or '미종료'}"
        )

    # 최소 턴 수 검증 (삼분법 흐름 등 다턴 확인이 필요한 시나리오)
    min_turns = scenario.get("min_turns")
    if min_turns is not None and turns < min_turns:
        result["passed"] = False
        result["failures"].append(f"턴 수 부족: expected≥{min_turns}, actual={turns}")

    # 체크리스트 항목 검증
    for exp in scenario.get("expected_checklist", []):
        item = find_checklist_item(final_checklist, exp["policy"], exp["label"])
        if item is None:
            result["passed"] = False
            result["failures"].append(f"항목 없음: [{exp['policy']}] {exp['label']}")
            continue
        actual_met = item["met"]
        expected_met = exp["met"]
        if actual_met != expected_met:
            result["passed"] = False
            result["failures"].append(
                f"met 불일치: [{exp['policy']}] {exp['label'][:30]}... expected={expected_met}, actual={actual_met}"
            )

    return result


def run_scenario(scenario: dict) -> dict:
    messages = [{"role": "user", "content": scenario["initial_query"]}]
    checklist: list[dict] = []
    session_id = None
    termination_type = None
    final_message = ""
    counselor_turns = 0

    for turn in range(MAX_TURNS):
        resp = requests.post(
            f"{API_URL}/chat",
            json={
                "messages": messages,
                "checklist": checklist,
                "session_id": session_id,
            },
            timeout=60,
        )
        if not resp.ok:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        resp.raise_for_status()
        data = resp.json()

        counselor_message = data["counselor_message"]
        checklist = data["checklist"]
        session_id = data.get("session_id")
        final_message = counselor_message

        counselor_turns += 1
        print(f"  [턴{counselor_turns} 상담사] {counselor_message[:120]}")

        termination_type = detect_termination(counselor_message)
        if termination_type:
            break

        citizen_reply = simulate_citizen(scenario["citizen_profile"], counselor_message)
        messages.append({"role": "assistant", "content": counselor_message})
        messages.append({"role": "user", "content": citizen_reply})

    actual_turns = counselor_turns
    result = evaluate_scenario(scenario, checklist, termination_type, turns=actual_turns)
    result["turns"] = actual_turns
    result["final_message_preview"] = final_message[:80]
    return result


def main():
    with open(SCENARIOS_FILE, encoding="utf-8") as f:
        scenarios = yaml.safe_load(f)["scenarios"]

    try:
        requests.get(f"{API_URL}/health", timeout=5).raise_for_status()
    except Exception:
        print(f"❌ 서버에 연결할 수 없습니다: {API_URL}")
        print("   uvicorn src.api:app --reload 로 서버를 먼저 실행하세요.")
        sys.exit(1)

    results = []
    for s in scenarios:
        print(f"\n[{s['id']}] {s['description']}")
        try:
            result = run_scenario(s)
        except Exception as e:
            result = {
                "id": s["id"],
                "passed": False,
                "failures": [f"오류: {e}"],
                "turns": 0,
                "final_message_preview": "",
            }

        icon = "✅" if result["passed"] else "❌"
        print(f"{icon} {result['id']} ({result['turns']}턴): {result['final_message_preview']}...")
        for f in result.get("failures", []):
            print(f"   ✗ {f}")
        results.append(result)

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"\n결과: {passed}/{total} 시나리오 통과")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
