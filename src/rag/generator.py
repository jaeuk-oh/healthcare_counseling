import os
import json
from openai import OpenAI
from .contacts_lookup import get_contacts_summary

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")

# ---------------------------------------------------------------------------
# 수정사항-1: 정책별 체크리스트 항목 (하드코딩)
# ---------------------------------------------------------------------------

POLICY_CRITERIA = {
    "암의료비지원": [
        "지원 대상 암종 해당 (소아: 전체 암, 성인: 5대 국가암+폐암)",
        "의료급여 수급자 또는 차상위 본인부담 경감대상자 여부 확인",
        "소득·재산 기준 충족 (중위소득 120% 이하)",
    ],
    "희귀질환의료비지원": [
        "희귀질환 코드(KCD) 해당 여부 확인",
        "건강보험 가입 또는 의료급여 수급자 여부 확인",
        "소득 기준 충족 여부 확인",
    ],
    "산정특례": [
        "건강보험 가입 여부 확인",
        "산정특례 대상 질환(암·희귀질환 등) 진단 여부",
    ],
    "국가암검진": [
        "검진 대상 연령·암종 해당 여부",
        "건강보험 가입 또는 의료급여 수급자 여부 확인",
    ],
}

# ---------------------------------------------------------------------------
# /classify — 시나리오에서 관련 정책 분류
# ---------------------------------------------------------------------------

CLASSIFY_FUNCTION = {
    "name": "classify_policies",
    "description": "시나리오에서 관련 가능성이 있는 의료비 지원 정책을 판별합니다",
    "parameters": {
        "type": "object",
        "required": ["relevant_policies"],
        "properties": {
            "relevant_policies": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": list(POLICY_CRITERIA.keys()),
                },
                "description": "관련 있는 정책 이름 목록. 불확실하면 포함.",
            }
        },
    },
}

CLASSIFY_SYSTEM = """당신은 보건소 의료비 지원 전문가입니다.
시나리오를 읽고 해당 가능성이 있는 정책을 모두 선택하세요.
불확실하면 포함하는 방향으로 선택하고, 명백히 관련 없는 것만 제외합니다."""


def classify(scenario: str) -> dict:
    client = OpenAI()
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": CLASSIFY_SYSTEM},
            {"role": "user", "content": scenario},
        ],
        tools=[{"type": "function", "function": CLASSIFY_FUNCTION}],
        tool_choice={"type": "function", "function": {"name": "classify_policies"}},
    )
    tool_call = response.choices[0].message.tool_calls[0]
    result = json.loads(tool_call.function.arguments)
    relevant = result.get("relevant_policies", [])

    checklist = [
        {
            "name": policy,
            "criteria": [{"label": label, "met": None} for label in POLICY_CRITERIA[policy]],
        }
        for policy in relevant
        if policy in POLICY_CRITERIA
    ]

    return {
        "checklist": checklist,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        },
    }


# ---------------------------------------------------------------------------
# /chat — 대화 기반 체크리스트 항목 업데이트
# ---------------------------------------------------------------------------

EVALUATE_FUNCTION = {
    "name": "update_checklist",
    "description": "대화 내용을 바탕으로 각 정책의 체크리스트 항목 충족 여부를 업데이트합니다",
    "parameters": {
        "type": "object",
        "required": ["updates"],
        "properties": {
            "updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["policy_name", "criteria"],
                    "properties": {
                        "policy_name": {"type": "string"},
                        "criteria": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["label", "met"],
                                "properties": {
                                    "label": {"type": "string"},
                                    "met": {"type": ["boolean", "null"]},
                                },
                            },
                        },
                    },
                },
            }
        },
    },
}

EVALUATE_SYSTEM = """당신은 보건소 의료비 지원 정책 전문가입니다.
대화 내용을 보고 각 정책의 체크리스트 항목이 충족되는지 판단하세요.

판단 기준:
- met: true  = 대화에서 해당 항목이 충족됨이 확인됨
- met: false = 대화에서 해당 항목이 충족되지 않음이 확인됨
- met: null  = 아직 대화에서 확인할 수 없음

규칙:
1. 이미 true/false로 확정된 항목은 null로 되돌리지 마세요
2. 대화에서 명확히 확인된 경우에만 true/false를 부여하세요
3. 암의료비지원 — 건강보험 가입자는 2021년 이후 신규 신청 불가이므로 의료급여수급자가 아니면 met: false
4. 산정특례 — 암 진단 + 건강보험 가입자면 원칙적으로 해당됨"""


def evaluate_criteria(conversation: str, checklist: list[dict]) -> dict:
    client = OpenAI()

    checklist_text = "\n".join(
        f"[{item['name']}]\n"
        + "\n".join(f"  - {c['label']} (현재: {c['met']})" for c in item["criteria"])
        for item in checklist
    )

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": EVALUATE_SYSTEM},
            {"role": "user", "content": f"체크리스트:\n{checklist_text}\n\n대화:\n{conversation}"},
        ],
        tools=[{"type": "function", "function": EVALUATE_FUNCTION}],
        tool_choice={"type": "function", "function": {"name": "update_checklist"}},
    )

    tool_call = response.choices[0].message.tool_calls[0]
    result = json.loads(tool_call.function.arguments)

    updates_by_name = {
        u["policy_name"]: {c["label"]: c["met"] for c in u["criteria"]}
        for u in result.get("updates", [])
    }

    updated_checklist = []
    for item in checklist:
        name = item["name"]
        criteria_updates = updates_by_name.get(name, {})
        updated_criteria = []
        for c in item["criteria"]:
            new_met = criteria_updates.get(c["label"], c["met"])
            # 확정된 값(true/false)은 null로 되돌리지 않음
            if c["met"] is not None and new_met is None:
                new_met = c["met"]
            updated_criteria.append({"label": c["label"], "met": new_met})
        updated_checklist.append({"name": name, "criteria": updated_criteria})

    return {
        "checklist": updated_checklist,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        },
    }


# ---------------------------------------------------------------------------
# /query (하위 호환) — 기존 전체 판단 방식 유지
# ---------------------------------------------------------------------------

RECOMMEND_FUNCTION = {
    "name": "recommend_policies",
    "description": "주어진 정책 문서를 근거로 신청 가능한 보건소 의료비 지원 정책을 추천하고, 해당 없는 상담은 담당 부서로 연결합니다",
    "parameters": {
        "type": "object",
        "required": ["recommendations"],
        "properties": {
            "recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["policy_name", "applicable", "eligibility_reasoning", "source_excerpts"],
                    "properties": {
                        "policy_name": {"type": "string"},
                        "applicable": {"type": "boolean"},
                        "eligibility_reasoning": {"type": "string"},
                        "source_excerpts": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["text", "article"],
                                "properties": {
                                    "text": {"type": "string"},
                                    "article": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            },
            "referral": {
                "description": "의료비 지원과 무관한 상담일 때만 채웁니다. 관련 있으면 null.",
                "type": ["object", "null"],
                "properties": {
                    "team": {"type": "string"},
                    "phone": {"type": "string"},
                    "reason": {"type": "string"},
                },
            },
        },
    },
}

SYSTEM_PROMPT = """당신은 보건소 의료비 지원 정책 전문 상담 보조 AI입니다.
아래 제공된 정책 문서만을 근거로 상담자의 상황에 맞는 정책을 판단합니다.

규칙:
1. 반드시 제공된 문서에서 실제 문장을 발췌하여 source_excerpts에 포함하세요
2. 문서에 없는 내용을 추론하거나 추가하지 마세요
3. applicable=true인 정책만 source_excerpts를 포함하세요
4. article 필드에는 해당 문서의 법령 조항 번호를 기재하세요
5. 의료비 지원과 전혀 무관한 상담(예: 예방접종, 정신건강, 치매, 모자보건 등)은
   recommendations를 빈 배열로 두고 referral에 아래 담당 부서 중 가장 적합한 곳을 기재하세요
6. applicable 필드는 반드시 eligibility_reasoning의 최종 판단과 일치해야 합니다.
   reasoning에서 지원 불가, 신청 불가, 중단, 해당 없음이라고 판단했다면 applicable은 반드시 false입니다.
   reasoning이 "불가능하다", "해당되지 않는다", "지원 중단"으로 끝난다면 applicable=false입니다.

보건소 담당 부서 연락처:
{contacts}

{rare_disease_section}
정책 문서:
{policy_docs}"""

RARE_DISEASE_SECTION = """희귀질환 코드 조회 결과:
{matches}
(위 질환은 희귀질환자 의료비지원사업 공식 대상 질환입니다. 판단 시 참고하세요.)

"""


def generate(query: str, policy_docs: list[dict], rare_matches: list[dict] | None = None) -> dict:
    client = OpenAI()
    policy_text = "\n\n---\n\n".join(
        f"[{d['policy_name']}]\n{d['text']}" for d in policy_docs
    )

    rare_section = ""
    if rare_matches:
        match_lines = "\n".join(
            f"- {m['korean_name']} (KCD: {m['kcd_code'] or '없음'})"
            for m in rare_matches
        )
        rare_section = RARE_DISEASE_SECTION.format(matches=match_lines)

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(
                contacts=get_contacts_summary(),
                policy_docs=policy_text,
                rare_disease_section=rare_section,
            )},
            {"role": "user", "content": query},
        ],
        tools=[{"type": "function", "function": RECOMMEND_FUNCTION}],
        tool_choice={"type": "function", "function": {"name": "recommend_policies"}},
    )

    tool_call = response.choices[0].message.tool_calls[0]
    result = json.loads(tool_call.function.arguments)

    # Deduplicate by policy_name, preferring applicable:true
    by_name: dict[str, dict] = {}
    for r in result.get("recommendations", []):
        name = r.get("policy_name")
        if name not in by_name or r.get("applicable"):
            by_name[name] = r

    # If reasoning says ineligible, override applicable to false
    INELIGIBLE_SIGNALS = [
        "신규지원 중단", "신규 지원 중단",
        "지원 불가능", "지원이 불가능", "지원신청 불가능", "신청 불가능",
        "신청 불가", "지원 불가", "불가능으로",
    ]
    recommendations = list(by_name.values())
    for r in recommendations:
        if r.get("applicable") and any(s in r.get("eligibility_reasoning", "") for s in INELIGIBLE_SIGNALS):
            r["applicable"] = False

    return {
        "recommendations": recommendations,
        "referral": result.get("referral"),
    }
