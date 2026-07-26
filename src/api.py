import os
import sys
import json
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

for key in ["OPENAI_API_KEY"]:
    if not os.getenv(key):
        print(f"❌ 필수 환경변수 없음: {key}", file=sys.stderr)
        sys.exit(1)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.rag.pipeline import run as rag_run
from src.rag.ingest import ingest
from src.rag.counselor import generate_counselor_response

from src.rag.generator import classify
from src.rag.retriever import retrieve
from src.rag.rare_disease_lookup import lookup as rare_lookup
from src.db import create_session, save_message, end_session, save_suggestion_feedback

app = FastAPI(title="보건소 의료비 지원 상담 AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str


class ChatTurn(BaseModel):
    role: str  # "user" (시민) | "assistant" (AI 상담사)
    content: str


class PolicyCriterion(BaseModel):
    label: str
    met: bool | None = None
    confirmable_by: str = "phone"


class PolicyChecklist(BaseModel):
    name: str
    criteria: list[PolicyCriterion]


class ChatRequest(BaseModel):
    messages: list[ChatTurn]
    checklist: list[PolicyChecklist] = []
    session_id: str | None = None


class ClassifyRequest(BaseModel):
    scenario: str


class SuggestionFeedbackRequest(BaseModel):
    """상담사가 AI 제안을 채택/수정/무시한 내역 (HITL 로그)."""
    session_id: str | None = None
    turn_index: int
    suggested_reply: str
    final_reply: str = ""
    action: str  # "accepted" | "edited" | "rejected"



class SessionEndRequest(BaseModel):
    scenario: str
    personality: str
    turns: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    session_id: str | None = None
    checklist: list[PolicyChecklist] = []


@app.post("/query")
async def query_endpoint(req: QueryRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query가 비어 있습니다")
    return rag_run(req.query)


@app.post("/ingest")
async def ingest_endpoint():
    count = ingest()
    return {"status": "ok", "documents_indexed": count}


@app.post("/classify")
async def classify_endpoint(req: ClassifyRequest):
    if not req.scenario.strip():
        raise HTTPException(status_code=400, detail="scenario가 비어 있습니다")
    result = classify(req.scenario)
    return {"checklist": result["checklist"], "token_usage": result["usage"]}


@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    messages_dict = [{"role": t.role, "content": t.content} for t in req.messages]
    checklist = [item.model_dump() for item in req.checklist]

    if not messages_dict:
        raise HTTPException(status_code=400, detail="messages가 비어 있습니다")

    query = messages_dict[-1]["content"]
    classify_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    # 첫 턴: 세션 생성 + 체크리스트 자동 분류
    session_id = req.session_id
    if not checklist:
        session_id = create_session(query)
        classify_result = classify(query)
        checklist = classify_result["checklist"]
        classify_usage = classify_result["usage"]

    # 이번 턴의 유저 메시지 저장 (마지막 메시지)
    last_user_index = len(messages_dict) - 1
    save_message(session_id, last_user_index, "user", query)

    policy_docs = retrieve(query)
    rare_matches = rare_lookup(query)

    is_first_turn = len(messages_dict) == 1
    counselor_result = generate_counselor_response(messages_dict, policy_docs, checklist, rare_matches, is_first_turn)

    # AI 응답 저장
    save_message(session_id, last_user_index + 1, "assistant", counselor_result["message"])

    total_usage = {
        "prompt_tokens": classify_usage["prompt_tokens"] + counselor_result["usage"]["prompt_tokens"],
        "completion_tokens": classify_usage["completion_tokens"] + counselor_result["usage"]["completion_tokens"],
        "total_tokens": classify_usage["total_tokens"] + counselor_result["usage"]["total_tokens"],
    }

    return {
        # 시민에게 그대로 읽어줄 수 있는 제안 답변 (하위 호환 키 유지)
        "counselor_message": counselor_result["message"],
        "suggested_reply": counselor_result["suggested_reply"],
        # 상담사 대상 내부 브리핑 (시민 비노출)
        "counselor_note": counselor_result["counselor_note"],
        "checklist": counselor_result["checklist"],
        "token_usage": total_usage,
        "session_id": session_id,
    }



@app.post("/session-end")
async def session_end_endpoint(req: SessionEndRequest):
    # Supabase 업데이트
    end_session(
        session_id=req.session_id,
        personality=req.personality,
        turns=req.turns,
        prompt_tokens=req.prompt_tokens,
        completion_tokens=req.completion_tokens,
        total_tokens=req.total_tokens,
        checklist=[item.model_dump() for item in req.checklist],
    )

    # fallback: 로컬 JSONL 로그 유지
    logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    log_entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "scenario": req.scenario,
        "personality": req.personality,
        "turns": req.turns,
        "prompt_tokens": req.prompt_tokens,
        "completion_tokens": req.completion_tokens,
        "total_tokens": req.total_tokens,
    }
    with open(logs_dir / "sessions.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    return {"status": "ok"}


@app.post("/suggestion-feedback")
async def suggestion_feedback_endpoint(req: SuggestionFeedbackRequest):
    """상담사가 AI 제안을 어떻게 처리했는지(HITL) 기록한다.

    이 로그가 '대화 데이터 기반 오류 발굴' 루프의 원천 데이터가 된다.
    (제안 대비 상담사 수정 내역 → 반복되는 수정 패턴 = 오류 케이스 후보)
    """
    valid_actions = {"accepted", "edited", "rejected"}
    if req.action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"action은 {valid_actions} 중 하나여야 합니다",
        )

    # Supabase 저장 (미설정 시 graceful skip)
    save_suggestion_feedback(
        session_id=req.session_id,
        turn_index=req.turn_index,
        suggested_reply=req.suggested_reply,
        final_reply=req.final_reply,
        action=req.action,
    )

    # fallback: 로컬 JSONL 로그 유지
    logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    log_entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "session_id": req.session_id,
        "turn_index": req.turn_index,
        "suggested_reply": req.suggested_reply,
        "final_reply": req.final_reply,
        "action": req.action,
    }
    with open(logs_dir / "suggestion_feedback.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    return {"status": "ok"}


@app.get("/health")
async def health():
    return {"status": "ok"}
