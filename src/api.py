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
from src.rag.citizen_simulator import load_personas, get_persona, simulate_citizen

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
    confirmable_by: str = "phone"
    # False 면 met=False 가 부적격이 아니라 분기 판별 결과라는 뜻 (generator.POLICY_CRITERIA 참고).
    # 클라이언트가 매 턴 체크리스트 전체를 되보내므로 여기 없으면 왕복 중에 값이 사라진다.
    decisive: bool = True


class PolicyChecklist(BaseModel):
    name: str
    criteria: list[PolicyCriterion]


class ChatRequest(BaseModel):
    messages: list[ChatTurn]
    checklist: list[PolicyChecklist] = []
    session_id: str | None = None


class ClassifyRequest(BaseModel):
    scenario: str


class TrainStartRequest(BaseModel):
    persona_id: str


class TrainTurnRequest(BaseModel):
    persona_id: str
    messages: list[ChatTurn]
    checklist: list[PolicyChecklist] = []
    session_id: str | None = None



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
        "counselor_message": counselor_result["message"],
        "checklist": counselor_result["checklist"],
        "token_usage": total_usage,
        "session_id": session_id,
    }



@app.get("/personas")
async def personas_endpoint():
    # citizen_profile(정답지)은 절대 클라이언트로 보내지 않는다.
    # description 도 마찬가지 — eval 용이라 기대 결과("→ 지원불가" 등)가 적혀 있어
    # 훈련자가 질문 전에 답을 알아버린다. 훈련자용 trainee_label 만 내보낸다.
    return [{"id": p["id"], "label": p["trainee_label"]} for p in load_personas()]


@app.post("/train/start")
async def train_start_endpoint(req: TrainStartRequest):
    persona = get_persona(req.persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="persona_id를 찾을 수 없습니다")

    initial_query = persona["initial_query"]
    session_id = create_session(initial_query)
    save_message(session_id, 0, "user", initial_query)
    classify_result = classify(initial_query)

    return {
        "citizen_message": initial_query,
        "checklist": classify_result["checklist"],
        "token_usage": classify_result["usage"],
        "session_id": session_id,
    }


@app.post("/train/turn")
async def train_turn_endpoint(req: TrainTurnRequest):
    persona = get_persona(req.persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="persona_id를 찾을 수 없습니다")

    messages_dict = [{"role": t.role, "content": t.content} for t in req.messages]
    checklist = [item.model_dump() for item in req.checklist]

    if not messages_dict:
        raise HTTPException(status_code=400, detail="messages가 비어 있습니다")

    citizen_turns = [m for m in messages_dict if m["role"] == "user"]
    query = citizen_turns[-1]["content"] if citizen_turns else persona["initial_query"]

    # 방금 트레이니(상담사 역)가 쓴 마지막 메시지를 저장
    last_index = len(messages_dict) - 1
    save_message(req.session_id, last_index, "assistant", messages_dict[-1]["content"])

    policy_docs = retrieve(query)
    rare_matches = rare_lookup(query)

    # checklist 코칭은 기존 상담사 엔진을 그대로 재사용한다. 히스토리 속 시민(AI) 발화에서
    # 체크리스트를 추출해주므로 역할을 뒤집을 필요가 없다. 함께 반환되는 message(LLM이 제안하는
    # "이상적인 상담사 답변")는 트레이니가 이미 직접 답했으므로 버린다.
    counselor_result = generate_counselor_response(
        messages_dict, policy_docs, checklist, rare_matches, is_first_turn=False
    )
    citizen_message = simulate_citizen(persona["citizen_profile"], messages_dict)

    # AI 민원인 응답 저장
    save_message(req.session_id, last_index + 1, "user", citizen_message)

    return {
        "citizen_message": citizen_message,
        "checklist": counselor_result["checklist"],
        "token_usage": counselor_result["usage"],
        "session_id": req.session_id,
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


@app.get("/health")
async def health():
    return {"status": "ok"}
