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
from src.rag.citizen import generate_citizen_message
from src.rag.hospital_lookup import find_nearest
from src.rag.generator import classify, evaluate_criteria

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
    role: str  # "citizen" | "counselor"
    content: str


class PolicyCriterion(BaseModel):
    label: str
    met: bool | None = None


class PolicyChecklist(BaseModel):
    name: str
    criteria: list[PolicyCriterion]


class ChatRequest(BaseModel):
    scenario: str
    messages: list[ChatTurn]
    checklist: list[PolicyChecklist] = []


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

    citizen_message = generate_citizen_message(req.scenario, messages_dict)

    checklist = [item.model_dump() for item in req.checklist]
    token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    if checklist and messages_dict:
        all_messages = messages_dict + [{"role": "citizen", "content": citizen_message}]
        conversation_text = "\n".join(
            f"{'시민' if m['role'] == 'citizen' else '상담사'}: {m['content']}"
            for m in all_messages
        )
        eval_result = evaluate_criteria(conversation_text, checklist)
        checklist = eval_result["checklist"]
        token_usage = eval_result["usage"]

    return {
        "citizen_message": citizen_message,
        "checklist": checklist,
        "token_usage": token_usage,
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
