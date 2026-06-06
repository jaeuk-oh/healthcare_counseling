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
6. 각 체크리스트 항목은 해당 조건만 독립적으로 판단하세요.
   전체 지원 가능 여부를 개별 항목에 투영하지 마세요.
   예: "진단 암종 해당" 항목은 진단된 암종이 목록(위·대장·간·유방·자궁경부암·폐암 등)에 있는지만 확인합니다.
   보험 유형이나 소득이 아직 미확인이어도 암종 해당 여부는 독립적으로 판단할 수 있습니다.
7. 체크리스트의 [VISIT] 항목(소득·재산 기준 등)은 전화상 판정하지 마세요.
   해당 내용이 언급되면 "정확한 기준은 내방하셔서 서류로 확인하셔야 합니다"라고 안내하세요.
   [VISIT] 항목은 checklist_updates에 포함하지 마세요.
7. [PHONE] 항목이 모두 충족됐다면 "지원 가능합니다"라고 단정하지 마세요.
   "관련 서류를 지참하신 후 내방하시면 지원 가능하실 것으로 보입니다"로 안내하고 내방을 권유하세요.
{first_turn_rule}

보건소 담당 부서 연락처:
{contacts}

{checklist_section}정책 문서:
{policy_docs}"""


FIRST_TURN_RULE = """6. 이 대화의 첫 번째 답변입니다. 반드시 "안녕하세요! 하남시 보건소 의료비 지원 상담사입니다."로 시작하세요.
   - 시민이 인사만 했다면 그 뒤에 "무엇을 도와드릴까요?" 를 덧붙이세요.
   - 시민이 바로 지원 관련 질문을 했다면 인사 뒤에 바로 필요한 추가 질문이나 안내를 이어가세요."""


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

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
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
        ],
        tools=[{"type": "function", "function": COUNSELOR_FUNCTION}],
        tool_choice={"type": "function", "function": {"name": "counselor_response"}},
    )

    tool_call = response.choices[0].message.tool_calls[0]
    result = json.loads(tool_call.function.arguments)

    updates_by_name = {
        u["policy_name"]: {c["label"]: c["met"] for c in u["criteria"]}
        for u in result.get("checklist_updates", [])
    }

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

    return {
        "message": result["message"],
        "checklist": updated_checklist,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        },
    }
