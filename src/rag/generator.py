import os
import json
from openai import OpenAI

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")

RECOMMEND_FUNCTION = {
    "name": "recommend_policies",
    "description": "주어진 정책 문서를 근거로 신청 가능한 보건소 의료비 지원 정책을 추천합니다",
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
            }
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

정책 문서:
{policy_docs}"""


def generate(query: str, policy_docs: list[dict]) -> dict:
    client = OpenAI()
    policy_text = "\n\n---\n\n".join(
        f"[{d['policy_name']}]\n{d['text']}" for d in policy_docs
    )

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(policy_docs=policy_text)},
            {"role": "user", "content": query},
        ],
        tools=[{"type": "function", "function": RECOMMEND_FUNCTION}],
        tool_choice={"type": "function", "function": {"name": "recommend_policies"}},
    )

    tool_call = response.choices[0].message.tool_calls[0]
    recommendations = json.loads(tool_call.function.arguments)["recommendations"]
    return {"recommendations": recommendations}
