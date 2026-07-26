import os
import sys
from datetime import datetime, timezone

try:
    from supabase import create_client, Client
    _SUPABASE_AVAILABLE = True
except ImportError:
    _SUPABASE_AVAILABLE = False

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not _SUPABASE_AVAILABLE:
        return None
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        return None
    _client = create_client(url, key)
    return _client


def create_session(scenario: str) -> str | None:
    client = _get_client()
    if not client:
        return None
    try:
        result = client.table("sessions").insert({"scenario": scenario}).execute()
        return result.data[0]["id"]
    except Exception as e:
        print(f"[db] create_session 실패: {e}", file=sys.stderr)
        return None


def save_message(session_id: str, turn_index: int, role: str, content: str) -> None:
    client = _get_client()
    if not client or not session_id:
        return
    try:
        client.table("messages").insert({
            "session_id": session_id,
            "turn_index": turn_index,
            "role": role,
            "content": content,
        }).execute()
    except Exception as e:
        print(f"[db] save_message 실패: {e}", file=sys.stderr)


def save_suggestion_feedback(
    session_id: str | None,
    turn_index: int,
    suggested_reply: str,
    final_reply: str,
    action: str,
) -> None:
    """상담사가 AI 제안을 채택/수정/무시한 내역(HITL 로그)을 저장한다.

    action: "accepted" | "edited" | "rejected"
    - accepted: 상담사가 제안을 그대로 사용
    - edited:   상담사가 제안을 수정해 사용 (final_reply에 수정본)
    - rejected: 상담사가 제안을 쓰지 않음
    """
    client = _get_client()
    if not client or not session_id:
        return
    try:
        client.table("suggestion_feedback").insert({
            "session_id": session_id,
            "turn_index": turn_index,
            "suggested_reply": suggested_reply,
            "final_reply": final_reply,
            "action": action,
        }).execute()
    except Exception as e:
        print(f"[db] save_suggestion_feedback 실패: {e}", file=sys.stderr)


def end_session(
    session_id: str,
    personality: str,
    turns: int,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    checklist: list,
) -> None:
    client = _get_client()
    if not client or not session_id:
        return
    try:
        client.table("sessions").update({
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "personality": personality,
            "total_turns": turns,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "final_checklist": checklist,
        }).eq("id", session_id).execute()
    except Exception as e:
        print(f"[db] end_session 실패: {e}", file=sys.stderr)
