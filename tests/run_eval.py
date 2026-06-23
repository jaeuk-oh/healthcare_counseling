"""자동화 평가 하네스 — 5개 시나리오 pass/fail 검증."""
import sys
import yaml
import requests
from pathlib import Path

API_URL = "http://localhost:8000"
SCENARIOS_FILE = Path(__file__).parent / "eval_scenarios.yaml"


def evaluate_scenario(scenario: dict, response: dict) -> dict:
    recommended = {
        r["policy_name"]
        for r in response.get("recommendations", [])
        if r.get("applicable")
    }
    expected = set(scenario["expected_policies"])
    also_ok = set(scenario.get("also_acceptable", []))

    recall = len(expected & recommended) / len(expected) if expected else 1.0
    unexpected = recommended - expected - also_ok
    precision_ok = len(unexpected) == 0
    passed = (recall == 1.0) and precision_ok

    return {
        "id": scenario["id"],
        "passed": passed,
        "recall": recall,
        "precision_ok": precision_ok,
        "recommended": sorted(recommended),
        "unexpected_policies": sorted(unexpected),
    }


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
        try:
            resp = requests.post(
                f"{API_URL}/query",
                json={"query": s["query"]},
                timeout=60,
            )
            resp.raise_for_status()
            result = evaluate_scenario(s, resp.json())
        except Exception as e:
            result = {
                "id": s["id"],
                "passed": False,
                "recall": 0.0,
                "precision_ok": False,
                "recommended": [],
                "unexpected_policies": [],
                "error": str(e),
            }

        icon = "✅" if result["passed"] else "❌"
        recall_pct = f"{result['recall']:.0%}"
        precision = "OK" if result["precision_ok"] else "FAIL"
        print(f"{icon} {result['id']}: recall={recall_pct}  precision={precision}  추천={result['recommended']}")
        if result.get("unexpected_policies"):
            print(f"   예상외 정책: {result['unexpected_policies']}")
        if result.get("error"):
            print(f"   오류: {result['error']}")
        results.append(result)

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"\n결과: {passed}/{total} 시나리오 통과")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
