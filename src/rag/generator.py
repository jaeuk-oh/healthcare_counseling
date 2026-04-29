import os
import json
from openai import OpenAI
from .contacts_lookup import get_contacts_summary

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")

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

    return {
        "recommendations": list(by_name.values()),
        "referral": result.get("referral"),
    }
