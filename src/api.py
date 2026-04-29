import os
import sys
from pathlib import Path

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


class ChatRequest(BaseModel):
    scenario: str
    messages: list[ChatTurn]


class HospitalSearchRequest(BaseModel):
    address: str
    cancer_type: str | None = None
    top_n: int = 5


@app.post("/query")
async def query_endpoint(req: QueryRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query가 비어 있습니다")
    return rag_run(req.query)


@app.post("/ingest")
async def ingest_endpoint():
    count = ingest()
    return {"status": "ok", "documents_indexed": count}


@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    messages_dict = [{"role": t.role, "content": t.content} for t in req.messages]

    citizen_message = generate_citizen_message(req.scenario, messages_dict)

    all_messages = messages_dict + [{"role": "citizen", "content": citizen_message}]
    conversation_text = "\n".join(
        f"{'시민' if m['role'] == 'citizen' else '상담사'}: {m['content']}"
        for m in all_messages
    )
    rag_result = rag_run(conversation_text)

    return {"citizen_message": citizen_message, "recommendations": rag_result["recommendations"]}


@app.post("/hospital-search")
async def hospital_search_endpoint(req: HospitalSearchRequest):
    if not req.address.strip():
        raise HTTPException(status_code=400, detail="address가 비어 있습니다")
    hospitals_path = Path(__file__).parent / "data" / "hospitals.json"
    if not hospitals_path.exists():
        raise HTTPException(status_code=503, detail="병원 데이터가 아직 준비되지 않았습니다. crawl_hospitals.py를 먼저 실행하세요.")
    results = find_nearest(req.address, req.cancer_type, req.top_n)
    return {"hospitals": results}


@app.get("/health")
async def health():
    return {"status": "ok"}
