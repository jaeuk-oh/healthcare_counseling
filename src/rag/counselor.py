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
1. 지원 자격 판단에 필요한 정보(보험 유형, 소득, 암 진단 여부 등)가 부족하면 자연스럽게 추가 질문하세요
2. 정책 문서에 있는 내용만 안내하세요. 문서에 없는 내용은 "확인이 필요합니다"라고 하세요
3. 구체적인 금액·서류·조건을 안내할 때는 문서의 내용을 근거로 인용하세요
4. 친절하고 명확한 구어체 존댓말로 답하세요 (2~4문장 내외)
5. checklist_updates에는 이번 대화에서 새로 확인된 항목만 업데이트하세요
   이미 true/false로 확정된 항목은 null로 되돌리지 마세요

보건소 담당 부서 연락처:
{contacts}

{checklist_section}정책 문서:
{policy_docs}"""


def generate_counselor_response(
    messages: list[dict],
    policy_docs: list[dict],
    checklist: list[dict],
    rare_matches: list[dict] | None = None,
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
            + "\n".join(f"  - {c['label']}: {c['met']}" for c in item["criteria"])
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
            new_met = criteria_updates.get(c["label"], c["met"])
            if c["met"] is not None and new_met is None:
                new_met = c["met"]
            updated_criteria.append({"label": c["label"], "met": new_met})
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
