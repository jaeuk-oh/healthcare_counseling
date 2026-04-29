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
6. 이미 말한 내용은 반복하지 마세요"""


def generate_citizen_message(scenario: str, messages: list[dict]) -> str:
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
    return response.choices[0].message.content.strip()
