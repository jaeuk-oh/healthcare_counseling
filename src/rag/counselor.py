import os
import json
from openai import OpenAI
from .contacts_lookup import get_contacts_summary

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")

COUNSELOR_FUNCTION = {
    "name": "counselor_response",
    "description": "보건소 의료비 지원 상담사로서 시민에게 답변하고 체크리스트를 업데이트합니다",
    "parameters": {
        "type": "object",
        "required": ["message", "checklist_updates"],
        "properties": {
            "message": {
                "type": "string",
                "description": "시민에게 전달할 상담사 답변 (구어체 존댓말)",
            },
            "checklist_updates": {
                "type": "array",
                "description": "이번 대화에서 새로 확인된 체크리스트 항목만 포함",
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
            },
        },
    },
}

COUNSELOR_SYSTEM = """당신은 하남시 보건소의 의료비 지원 상담사입니다.
시민의 상황을 파악하고, 아래 정책 문서를 근거로 지원 가능한 제도를 안내합니다.

규칙:
1. 지원 자격 판단에 필요한 정보가 부족하면 자연스럽게 추가 질문하세요.
   체크리스트 항목은 위에서 아래 순서대로 확인하세요. 앞 항목이 미확인인 상태에서 뒤 항목을 먼저 물어보지 마세요.
2. 정책 문서에 있는 내용만 안내하세요. 문서에 없는 내용은 "확인이 필요합니다"라고 하세요
3. 구체적인 금액·서류·조건을 안내할 때는 문서의 내용을 근거로 인용하세요
4. 친절하고 명확한 구어체 존댓말로 답하세요 (2~4문장 내외)
5. checklist_updates에는 이번 대화에서 새로 확인된 항목만 업데이트하세요
   이미 true/false로 확정된 항목은 null로 되돌리지 마세요
   시민의 발화에서 정보를 확인했으면, 내방 안내·지원불가 안내 여부와 무관하게 반드시 해당 [PHONE] 항목을 같은 턴에 업데이트하세요.
   예: 시민이 "건강보험 가입자이고 2020년 수검, 2022년 위암 진단"이라고 했다면
       보험유형(false), 수검일(true), 진단일(true), 암종(true)을 모두 즉시 업데이트해야 합니다.
6. 각 체크리스트 항목은 해당 조건만 독립적으로 판단하세요.
   전체 지원 가능 여부를 개별 항목에 투영하지 마세요.
   예: "진단 암종 해당" 항목은 진단된 암종이 목록(위·대장·간·유방·자궁경부암·폐암 등)에 있는지만 확인합니다.
   보험 유형이나 소득이 아직 미확인이어도 암종 해당 여부는 독립적으로 판단할 수 있습니다.
7. 체크리스트의 [VISIT] 항목(소득·재산 기준 등)은 전화상 판정하지 마세요.
   해당 내용이 언급되면 "정확한 기준은 내방하셔서 서류로 확인하셔야 합니다"라고 안내하세요.
   [VISIT] 항목은 checklist_updates에 포함하지 마세요.
7. [PHONE] 항목이 모두 충족됐다면 "지원 가능합니다"라고 단정하지 마세요.
   "관련 서류를 지참하신 후 내방하시면 지원 가능하실 것으로 보입니다"로 안내하고 내방을 권유하세요.

성인암의료비지원 특칙:
- '보험 유형 확인' 항목: 의료급여 수급자 또는 차상위 본인부담 경감대상자이면 met: true, 건강보험 가입자이면 met: false
- 의료급여 수급자(met: true)로 확인되면: 수검일·진단일·보험료 항목은 건강보험 가입자 전용이므로 확인 불필요. 암종 확인 후 내방 안내로 이어가세요.
- 건강보험 가입자(met: false)로 확인되면: 즉시 종료하지 말고 수검일·진단일을 전화로 확인하세요.
  - 2021.6.30 이전 국가암검진 수검 AND 2023.6.30 이전 암 진단 → 둘 다 해당이면 건강보험료 기준 확인을 위해 내방 안내하세요.
  - 둘 중 하나라도 해당 없으면 아래를 안내하고 상담을 마무리하세요:
    1. 보건소 암의료비지원 해당 없음.
    2. 산정특례: 치료받으시는 병원에서 신청 가능합니다 (보건소 관할 아님).
    3. 재난적 의료비 지원: 건강보험공단(1577-1000)에서 요건 확인 및 신청 가능합니다.
{first_turn_rule}

보건소 담당 부서 연락처:
{contacts}

{checklist_section}정책 문서:
{policy_docs}"""


FIRST_TURN_RULE = """6. 이 대화의 첫 번째 답변입니다. 반드시 "안녕하세요! 하남시 보건소 의료비 지원 상담사입니다."로 시작하세요.
   - 시민이 인사만 했다면 그 뒤에 "무엇을 도와드릴까요?" 를 덧붙이세요.
   - 시민이 바로 지원 관련 질문을 했다면 인사 뒤에 바로 필요한 추가 질문이나 안내를 이어가세요."""


# function calling은 스키마를 유도할 뿐 보장하지 않는다. /chat에서도 checklist_updates
# 원소가 object가 아닌 문자열로 오는 위반을 실측했고(500), 파싱 단계에서 걸러낸다.
PARSE_ATTEMPTS = 2


def parse_checklist_updates(result: dict | None) -> dict[str, dict]:
    """LLM의 checklist_updates를 {정책명: {라벨: met}} 로 정규화한다.

    스키마를 지키지 않은 항목은 조용히 버린다. 잘못 해석해서 상태를 오염시키는 것보다
    업데이트를 누락하는 쪽이 안전하다 (누락은 다음 턴에 다시 물어보면 복구된다).
    """
    if not isinstance(result, dict):
        return {}
    updates: dict[str, dict] = {}
    for u in result.get("checklist_updates", []) or []:
        if not isinstance(u, dict):
            continue
        name = u.get("policy_name")
        criteria = u.get("criteria")
        if not name or not isinstance(criteria, list):
            continue
        updates[name] = {
            c["label"]: c.get("met")
            for c in criteria
            if isinstance(c, dict) and c.get("label")
        }
    return updates


def apply_checklist_guardrails(
    checklist: list[dict],
    updates_by_name: dict[str, dict],
) -> list[dict]:
    """LLM이 제안한 체크리스트 변경을 코드 레벨 가드레일로 걸러 최종 상태를 만든다.

    LLM 출력과 무관하게 두 가지를 강제한다.
    1. visit 항목 동결 — 전화로 판정 불가한 항목은 항상 met=None
    2. 확정값 보호 — 이미 true/false로 확정된 항목은 None으로 되돌리지 못함
       (true→false 같은 확정값 간 정정은 허용한다. 상담 중 사실이 정정될 수 있기 때문)
    """
    updated_checklist = []
    for item in checklist:
        name = item["name"]
        criteria_updates = updates_by_name.get(name, {})
        updated_criteria = []
        for c in item["criteria"]:
            if c.get("confirmable_by") == "visit":
                updated_criteria.append({"label": c["label"], "confirmable_by": "visit", "met": None})
                continue
            new_met = criteria_updates.get(c["label"], c["met"])
            if c["met"] is not None and new_met is None:
                new_met = c["met"]
            updated_criteria.append({"label": c["label"], "confirmable_by": c.get("confirmable_by", "phone"), "met": new_met})
        updated_checklist.append({"name": name, "criteria": updated_criteria})
    return updated_checklist


def generate_counselor_response(
    messages: list[dict],
    policy_docs: list[dict],
    checklist: list[dict],
    rare_matches: list[dict] | None = None,
    is_first_turn: bool = False,
) -> dict:
    client = OpenAI()

    policy_text = "\n\n---\n\n".join(
        f"[{d['policy_name']}]\n{d['text']}" for d in policy_docs
    )

    if rare_matches:
        rare_lines = "\n".join(
            f"- {m['korean_name']} (KCD: {m['kcd_code'] or '없음'})"
            for m in rare_matches
        )
        policy_text += (
            f"\n\n---\n\n[희귀질환 코드 조회 결과]\n{rare_lines}\n"
            "(위 질환은 희귀질환자 의료비지원사업 공식 대상 질환입니다.)"
        )

    checklist_section = ""
    if checklist:
        lines = "\n".join(
            f"[{item['name']}]\n"
            + "\n".join(
                f"  - [{c.get('confirmable_by', 'phone').upper()}] {c['label']}: {c['met']}"
                for c in item["criteria"]
            )
            for item in checklist
        )
        checklist_section = f"현재 체크리스트 상태:\n{lines}\n\n"

    request_messages = [
        {
            "role": "system",
            "content": COUNSELOR_SYSTEM.format(
                contacts=get_contacts_summary(),
                policy_docs=policy_text,
                checklist_section=checklist_section,
                first_turn_rule=f"\n{FIRST_TURN_RULE}" if is_first_turn else "",
            ),
        },
        *messages,
    ]

    result = None
    for attempt in range(PARSE_ATTEMPTS):
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=request_messages,
            tools=[{"type": "function", "function": COUNSELOR_FUNCTION}],
            tool_choice={"type": "function", "function": {"name": "counselor_response"}},
        )
        tool_call = response.choices[0].message.tool_calls[0]
        try:
            result = json.loads(tool_call.function.arguments)
            break
        except json.JSONDecodeError:
            if attempt == PARSE_ATTEMPTS - 1:
                raise

    updated_checklist = apply_checklist_guardrails(checklist, parse_checklist_updates(result))

    # 상담 문구는 대체하지 않는다. 없는 답변을 코드가 지어내면 그게 곧 오안내다.
    message = result.get("message") if isinstance(result, dict) else None
    if not message:
        raise RuntimeError("LLM이 상담 문구(message)를 반환하지 않았습니다")

    return {
        "message": message,
        "checklist": updated_checklist,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        },
    }
