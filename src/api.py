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

app = FastAPI(title="보건소 의료비 지원 상담 AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str


@app.post("/query")
async def query_endpoint(req: QueryRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query가 비어 있습니다")
    return rag_run(req.query)


@app.post("/ingest")
async def ingest_endpoint():
    count = ingest()
    return {"status": "ok", "documents_indexed": count}


@app.get("/health")
async def health():
    return {"status": "ok"}
