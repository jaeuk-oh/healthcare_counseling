import os
from functools import lru_cache
from pathlib import Path

import yaml
from openai import OpenAI

CITIZEN_MODEL = os.getenv("CITIZEN_MODEL", "gpt-4o-mini")
PERSONAS_FILE = Path(__file__).parent.parent / "data" / "personas.yaml"


@lru_cache
def load_personas() -> list[dict]:
    with open(PERSONAS_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)["scenarios"]


def get_persona(persona_id: str) -> dict | None:
    for p in load_personas():
        if p["id"] == persona_id:
            return p
    return None


def simulate_citizen(citizen_profile: str, messages: list[dict]) -> str:
    """훈련 모드에서 AI가 민원인을 연기한다.

    메인 대화 배열은 user=시민 / assistant=상담사 컨벤션을 쓰지만, 시민을 연기하는
    모델 입장에서는 상담사의 말이 자신에게 온 "user" 입력이고 자신의 과거 발화가
    "assistant"다. 그대로 넘기면 모델이 자기 자신을 상담사로 착각하므로 역할을 뒤집는다.
    """
    swapped = [
        {"role": "user" if m["role"] == "assistant" else "assistant", "content": m["content"]}
        for m in messages
    ]

    client = OpenAI()
    response = client.chat.completions.create(
        model=CITIZEN_MODEL,
        messages=[{"role": "system", "content": citizen_profile}, *swapped],
        max_tokens=150,
    )
    return response.choices[0].message.content.strip()
