"""코드 레벨 가드레일 결정적 검증 — LLM/서버 없이 순수 로직만 테스트.

멀티턴 eval(run_counselor_eval.py)은 LLM이 실제로 잘못된 출력을 냈을 때만
가드레일이 발동하므로, 통과해도 "가드레일이 막았다"를 증명하지 못한다.
여기서는 LLM이 낼 수 있는 최악의 출력을 직접 주입해 가드레일 동작을 확정적으로 검증한다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.counselor import apply_checklist_guardrails, parse_checklist_updates
from src.rag.generator import valid_recommendations


def make_checklist(met_values: dict) -> list[dict]:
    return [
        {
            "name": "성인암의료비지원",
            "criteria": [
                {"label": "보험 유형 확인", "confirmable_by": "phone", "met": met_values.get("보험", None)},
                {"label": "진단 암종 해당", "confirmable_by": "phone", "met": met_values.get("암종", None)},
                {"label": "건강보험료 기준 충족", "confirmable_by": "visit", "met": met_values.get("보험료", None)},
            ],
        }
    ]


def get_met(checklist: list[dict], label: str):
    for c in checklist[0]["criteria"]:
        if c["label"] == label:
            return c["met"]
    raise KeyError(label)


CASES = []


def case(name):
    def deco(fn):
        CASES.append((name, fn))
        return fn
    return deco


# --- 가드레일 1: visit 항목 동결 -------------------------------------------

@case("visit 항목은 LLM이 true로 판정해도 None으로 동결된다")
def _():
    result = apply_checklist_guardrails(
        make_checklist({}),
        {"성인암의료비지원": {"건강보험료 기준 충족": True}},
    )
    assert get_met(result, "건강보험료 기준 충족") is None


@case("visit 항목은 LLM이 false로 판정해도 None으로 동결된다")
def _():
    result = apply_checklist_guardrails(
        make_checklist({}),
        {"성인암의료비지원": {"건강보험료 기준 충족": False}},
    )
    assert get_met(result, "건강보험료 기준 충족") is None


@case("visit 항목은 이전 턴에 값이 있었더라도 None으로 동결된다")
def _():
    result = apply_checklist_guardrails(make_checklist({"보험료": True}), {})
    assert get_met(result, "건강보험료 기준 충족") is None


# --- 가드레일 3: 확정값 보호 -----------------------------------------------

@case("확정된 true를 LLM이 null로 되돌리려 하면 차단된다")
def _():
    result = apply_checklist_guardrails(
        make_checklist({"보험": True}),
        {"성인암의료비지원": {"보험 유형 확인": None}},
    )
    assert get_met(result, "보험 유형 확인") is True


@case("확정된 false를 LLM이 null로 되돌리려 하면 차단된다")
def _():
    result = apply_checklist_guardrails(
        make_checklist({"보험": False}),
        {"성인암의료비지원": {"보험 유형 확인": None}},
    )
    assert get_met(result, "보험 유형 확인") is False


@case("LLM이 업데이트를 아예 누락해도 확정값은 유지된다")
def _():
    result = apply_checklist_guardrails(make_checklist({"보험": True, "암종": False}), {})
    assert get_met(result, "보험 유형 확인") is True
    assert get_met(result, "진단 암종 해당") is False


@case("확정값 간 정정(true→false)은 허용된다")
def _():
    result = apply_checklist_guardrails(
        make_checklist({"보험": True}),
        {"성인암의료비지원": {"보험 유형 확인": False}},
    )
    assert get_met(result, "보험 유형 확인") is False


@case("미확인(None) 항목의 정상 확정은 통과된다")
def _():
    result = apply_checklist_guardrails(
        make_checklist({}),
        {"성인암의료비지원": {"보험 유형 확인": True}},
    )
    assert get_met(result, "보험 유형 확인") is True


# --- LLM 출력 구조 검증 (function calling 스키마 위반 방어) -----------------
# 아래 두 케이스는 실제 eval 실행 중 500 에러로 관측된 LLM 출력이다.

@case("recommendations 원소가 문자열이면 걸러낸다 (실측된 500 원인)")
def _():
    result = valid_recommendations({"recommendations": ["암의료비지원", "국가암검진"]})
    assert result == [], result


@case("정상 항목과 깨진 항목이 섞이면 정상 항목만 남긴다")
def _():
    result = valid_recommendations({
        "recommendations": [
            {"policy_name": "암의료비지원", "applicable": True},
            "국가암검진",
            {"applicable": False},  # policy_name 누락
        ]
    })
    assert len(result) == 1, result
    assert result[0]["policy_name"] == "암의료비지원"


@case("recommendations가 리스트가 아니면 빈 결과를 준다")
def _():
    assert valid_recommendations({"recommendations": "없음"}) == []


@case("result 자체가 dict가 아니어도 죽지 않는다")
def _():
    assert valid_recommendations(["암의료비지원"]) == []
    assert valid_recommendations(None) == []


@case("checklist_updates 원소가 문자열이면 걸러낸다 (실측된 /chat 500 원인)")
def _():
    assert parse_checklist_updates({"checklist_updates": ["성인암의료비지원"]}) == {}


@case("criteria가 리스트가 아닌 업데이트는 버린다")
def _():
    assert parse_checklist_updates({
        "checklist_updates": [{"policy_name": "성인암의료비지원", "criteria": "보험 유형 true"}]
    }) == {}


@case("정상 업데이트는 {정책: {라벨: met}} 로 정규화된다")
def _():
    result = parse_checklist_updates({
        "checklist_updates": [
            {
                "policy_name": "성인암의료비지원",
                "criteria": [
                    {"label": "보험 유형 확인", "met": True},
                    "깨진 항목",
                    {"met": False},  # label 누락
                ],
            }
        ]
    })
    assert result == {"성인암의료비지원": {"보험 유형 확인": True}}, result


def main():
    failures = []
    for name, fn in CASES:
        try:
            fn()
            print(f"✅ {name}")
        except AssertionError as e:
            print(f"❌ {name}\n   {e}")
            failures.append(name)

    print(f"\n결과: {len(CASES) - len(failures)}/{len(CASES)} 통과")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
