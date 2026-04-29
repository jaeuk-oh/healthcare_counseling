import json
from functools import lru_cache
from pathlib import Path

JSON_PATH = Path(__file__).parent.parent / "data" / "contacts.json"


@lru_cache(maxsize=1)
def get_contacts_summary() -> str:
    """LLM 시스템 프롬프트에 삽입할 부서 연락처 요약."""
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    lines = []
    for team in data:
        duties = [m["main_duty"] for m in team["members"] if m["main_duty"]]
        duty_str = duties[0] if duties else ""
        lines.append(f"- {team['team']} ({team['phone']}): {duty_str}")
    return "\n".join(lines)
