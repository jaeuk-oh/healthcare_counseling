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
from src.rag.hospital_lookup import find_nearest
from src.rag.generator import classify
from src.rag.retriever import retrieve
from src.rag.rare_disease_lookup import lookup as rare_lookup
from src.db import create_session, save_message, end_session

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


class PolicyChecklist(BaseModel):
    name: str
    criteria: list[PolicyCriterion]


class ChatRequest(BaseModel):
    messages: list[ChatTurn]
    checklist: list[PolicyChecklist] = []
    session_id: str | None = None


class ClassifyRequest(BaseModel):
    scenario: str


class HospitalSearchRequest(BaseModel):
    address: str
    cancer_type: str | None = None
    top_n: int = 5


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

    counselor_result = generate_counselor_response(messages_dict, policy_docs, checklist, rare_matches)

    # AI 응답 저장
    save_message(session_id, last_user_index + 1, "assistant", counselor_result["message"])

    total_usage = {
        "prompt_tokens": classify_usage["prompt_tokens"] + counselor_result["usage"]["prompt_tokens"],
        "completion_tokens": classify_usage["completion_tokens"] + counselor_result["usage"]["completion_tokens"],
        "total_tokens": classify_usage["total_tokens"] + counselor_result["usage"]["total_tokens"],
    }

    return {
        "counselor_message": counselor_result["message"],
        "checklist": counselor_result["checklist"],
        "token_usage": total_usage,
        "session_id": session_id,
    }


@app.post("/hospital-search")
async def hospital_search_endpoint(req: HospitalSearchRequest):
    if not req.address.strip():
        raise HTTPException(status_code=400, detail="address가 비어 있습니다")
    hospitals_path = Path(__file__).parent / "data" / "hospitals.json"
    if not hospitals_path.exists():
        raise HTTPException(status_code=503, detail="병원 데이터가 아직 준비되지 않았습니다. crawl_hospitals.py를 먼저 실행하세요.")
    results = find_nearest(req.address, req.cancer_type, req.top_n)
    return {"hospitals": results}


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


@app.get("/health")
async def health():
    return {"status": "ok"}
