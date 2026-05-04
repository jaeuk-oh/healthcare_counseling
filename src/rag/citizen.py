import os
from openai import OpenAI

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")

CITIZEN_SYSTEM = """당신은 보건소에 전화해서 의료비 지원을 문의하는 시민입니다.

당신의 상황: {scenario}

규칙:
1. 자연스러운 구어체 한국어 존댓말로 말하세요
2. 한 번에 1~3문장으로 간결하게 말하세요
3. 첫 발화는 전화를 건 것처럼 인사하며 상황을 설명하세요
4. 상담사가 추가 정보를 물으면 자연스럽게 답하세요
5. 의료비 지원 정책 용어는 모르는 일반 시민처럼 행동하세요
6. 이미 말한 내용은 반복하지 마세요
7. 시나리오에 [성격: ...] 태그가 있으면 그 성격 그대로 말하세요.
   예) "말을 더듬고 문장을 자주 중간에 끊음" → "저... 저는 위암을 진단받았는데요, 그... 지원이 되는지 해서요..."
   예) "매우 짧고 단답식" → "위암이요." / "네." / "모르겠어요."
   예) "짜증이 섞인 말투" → "아 그거 그냥 빨리 알려주시면 안 돼요?"
   예) "모든 걸 다 해달라는 민원형" → "그럼 신청서도 대신 써주시는 거죠? 서류도 다 알려주세요."

절대 금지:
- 정책 내용을 설명하거나 안내하지 마세요. 당신은 정책을 모릅니다.
- "~을 신청하시면 됩니다", "~에 해당하십니다", "~를 확인해 보세요" 같은 상담사 말투 금지
- 조언·안내·추천을 하지 마세요. 오직 질문에 답하거나 상황을 설명하세요.
- 당신은 도움을 받으러 전화한 시민입니다. 도움을 주는 역할이 아닙니다."""


def generate_citizen_message(scenario: str, messages: list[dict]) -> dict:
    client = OpenAI()
    # 시민 LLM 관점: 상담사 = user, 시민(본인) = assistant
    oai_messages = [
        {"role": "user" if m["role"] == "counselor" else "assistant", "content": m["content"]}
        for m in messages
    ]
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": CITIZEN_SYSTEM.format(scenario=scenario)},
            *oai_messages,
        ],
        max_tokens=200,
    )
    return {
        "message": response.choices[0].message.content.strip(),
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        },
    }
