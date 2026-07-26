"""HITL 피드백 로그 → 오류 케이스 후보 발굴 파이프라인.

상담사가 AI 제안(suggested_reply)을 채택/수정/무시한 내역(/suggestion-feedback 로그)을
읽어, "AI가 어디서 자주 틀리거나 부족한가"를 데이터로 도출한다.

핵심 아이디어:
- 상담사가 제안에서 **뺀** 표현(removed)  → AI 과잉·부정확 표현 후보
  (INELIGIBLE_SIGNALS 같은 코드 가드레일에 추가할 키워드 후보)
- 상담사가 제안에 **보탠** 표현(added)    → AI 누락 정보 후보
  (정책 문서·프롬프트 보강 후보)
- 통째로 **무시된**(rejected) 제안         → 방향 자체가 틀린 케이스

의존성 없는 코어(difflib) + 선택적 LLM 군집화(--llm, OpenAI).

사용 예:
    python scripts/analyze_feedback.py                       # logs/suggestion_feedback.jsonl 분석
    python scripts/analyze_feedback.py --input path.jsonl
    python scripts/analyze_feedback.py --supabase            # Supabase에서 조회
    python scripts/analyze_feedback.py --json report.json    # 머신용 리포트 저장
    python scripts/analyze_feedback.py --llm                 # LLM으로 오류 유형 군집화 + 규칙 제안
"""
import os
import sys
import json
import argparse
import difflib
import re
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

DEFAULT_LOG = Path(__file__).parent.parent / "logs" / "suggestion_feedback.jsonl"

VALID_ACTIONS = {"accepted", "edited", "rejected"}

# 조사/구두점을 떼어내 표현을 정규화하기 위한 후행 조사 목록 (완벽하지 않아도 신호는 잡힌다)
_TRAILING_JOSA = ("으로", "로", "은", "는", "이", "가", "을", "를", "에", "의", "도", "만", "과", "와")


# ---------------------------------------------------------------------------
# 로그 적재
# ---------------------------------------------------------------------------

def load_from_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def load_from_supabase(limit: int) -> list[dict]:
    from dotenv import load_dotenv
    load_dotenv()
    from src.db import fetch_suggestion_feedback
    return fetch_suggestion_feedback(limit)


# ---------------------------------------------------------------------------
# 텍스트 diff — 상담사가 뺀/보탠 표현 추출
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    """공백 기준 토큰화. 한국어는 어절이 대체로 공백으로 구분되므로 신호 추출에 충분."""
    return [t for t in re.split(r"\s+", text.strip()) if t]


def _clean_phrase(tokens: list[str]) -> str:
    phrase = " ".join(tokens).strip()
    # 양끝 구두점 제거
    phrase = phrase.strip(" .,!?~…\"'()[]").strip()
    return phrase


def _normalize_signal(phrase: str) -> str:
    """조사·구두점을 떼어 반복 표현이 같은 키로 집계되게 한다."""
    p = phrase.strip(" .,!?~…\"'()[]").strip()
    for josa in _TRAILING_JOSA:
        if p.endswith(josa) and len(p) > len(josa) + 1:
            p = p[: -len(josa)]
            break
    return p.strip()


def diff_phrases(suggested: str, final: str) -> tuple[list[str], list[str]]:
    """(removed, added) — 제안에서 빠진 표현, 상담사가 보탠 표현."""
    a = _tokenize(suggested)
    b = _tokenize(final)
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    removed, added = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace"):
            phrase = _clean_phrase(a[i1:i2])
            if phrase:
                removed.append(phrase)
        if tag in ("insert", "replace"):
            phrase = _clean_phrase(b[j1:j2])
            if phrase:
                added.append(phrase)
    return removed, added


# ---------------------------------------------------------------------------
# 분석
# ---------------------------------------------------------------------------

def analyze(entries: list[dict], min_count: int = 2, top_n: int = 15) -> dict:
    total = len(entries)
    action_counts = Counter(e.get("action") for e in entries)

    removed_counter: Counter = Counter()
    added_counter: Counter = Counter()
    # 정규화 키 → 대표 원문 (사람이 읽기 좋게)
    removed_repr: dict[str, str] = {}
    added_repr: dict[str, str] = {}

    edited_pairs = []
    rejected_samples = []

    for e in entries:
        action = e.get("action")
        suggested = (e.get("suggested_reply") or "").strip()
        final = (e.get("final_reply") or "").strip()

        if action == "edited" and suggested and final and suggested != final:
            removed, added = diff_phrases(suggested, final)
            for p in removed:
                key = _normalize_signal(p)
                if key:
                    removed_counter[key] += 1
                    removed_repr.setdefault(key, p)
            for p in added:
                key = _normalize_signal(p)
                if key:
                    added_counter[key] += 1
                    added_repr.setdefault(key, p)
            edited_pairs.append({
                "turn": e.get("turn_index"),
                "session_id": e.get("session_id"),
                "suggested": suggested,
                "final": final,
                "removed": removed,
                "added": added,
            })
        elif action == "rejected" and suggested:
            rejected_samples.append({
                "turn": e.get("turn_index"),
                "session_id": e.get("session_id"),
                "suggested": suggested,
            })

    def rank(counter: Counter, repr_map: dict) -> list[dict]:
        return [
            {"phrase": repr_map.get(k, k), "normalized": k, "count": c}
            for k, c in counter.most_common(top_n)
            if c >= min_count
        ]

    accepted = action_counts.get("accepted", 0)
    edited = action_counts.get("edited", 0)
    rejected = action_counts.get("rejected", 0)

    return {
        "total": total,
        "actions": {"accepted": accepted, "edited": edited, "rejected": rejected},
        "acceptance_rate": round(accepted / total, 3) if total else None,
        "revision_rate": round((edited + rejected) / total, 3) if total else None,
        "overclaim_candidates": rank(removed_counter, removed_repr),   # 뺀 표현 = 과잉·부정확
        "missing_info_candidates": rank(added_counter, added_repr),    # 보탠 표현 = 누락
        "rejected_samples": rejected_samples[:top_n],
        "edited_pairs": edited_pairs,
    }


# ---------------------------------------------------------------------------
# 선택적 LLM 군집화 — 오류 유형 요약 + 가드레일 규칙 제안
# ---------------------------------------------------------------------------

def llm_cluster(report: dict, model: str) -> dict | None:
    pairs = report["edited_pairs"][:30]
    rejected = report["rejected_samples"][:15]
    if not pairs and not rejected:
        return None

    from dotenv import load_dotenv
    load_dotenv()
    from openai import OpenAI

    samples = {
        "edited": [{"suggested": p["suggested"], "final": p["final"]} for p in pairs],
        "rejected": [{"suggested": r["suggested"]} for r in rejected],
    }

    system = (
        "당신은 보건소 상담 보조 AI의 품질을 개선하는 분석가입니다. "
        "상담사가 AI 제안을 수정(edited)하거나 무시(rejected)한 사례들을 보고, "
        "반복되는 오류 유형을 군집화하고, 각 유형에 대해 코드 가드레일이나 프롬프트 규칙 후보를 제안하세요."
    )
    user = (
        "다음은 상담사 피드백 로그 샘플입니다(JSON). suggested는 AI 제안, final은 상담사 최종본입니다.\n\n"
        f"{json.dumps(samples, ensure_ascii=False, indent=2)}\n\n"
        "propose_error_cases 함수로 답하세요."
    )
    func = {
        "name": "propose_error_cases",
        "description": "반복 오류 유형과 가드레일 규칙 후보",
        "parameters": {
            "type": "object",
            "required": ["error_cases"],
            "properties": {
                "error_cases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "description", "proposed_rule"],
                        "properties": {
                            "name": {"type": "string", "description": "오류 유형 이름"},
                            "description": {"type": "string", "description": "무엇이 반복적으로 잘못되는가"},
                            "proposed_rule": {"type": "string", "description": "코드 가드레일 또는 프롬프트 규칙 후보"},
                            "candidate_keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "INELIGIBLE_SIGNALS 같은 키워드 후보(있으면)",
                            },
                        },
                    },
                }
            },
        },
    }

    client = OpenAI()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        tools=[{"type": "function", "function": func}],
        tool_choice={"type": "function", "function": {"name": "propose_error_cases"}},
    )
    return json.loads(resp.choices[0].message.tool_calls[0].function.arguments)


# ---------------------------------------------------------------------------
# 리포트 출력
# ---------------------------------------------------------------------------

def print_report(report: dict, llm_result: dict | None) -> None:
    a = report["actions"]
    print("=" * 60)
    print("HITL 피드백 분석 리포트")
    print("=" * 60)
    print(f"총 피드백: {report['total']}건")
    if report["total"] == 0:
        print("\n로그가 비어 있습니다. 상담사가 /suggestion-feedback 로 제안을 처리하면 데이터가 쌓입니다.")
        return
    print(f"  채택(accepted): {a['accepted']}  수정(edited): {a['edited']}  무시(rejected): {a['rejected']}")
    print(f"  제안 채택률: {report['acceptance_rate']}   수정·무시율: {report['revision_rate']}")

    print("\n[과잉·부정확 표현 후보] — 상담사가 제안에서 자주 뺀 표현")
    print("  → 코드 가드레일(예: INELIGIBLE_SIGNALS) 또는 프롬프트 금지 규칙 후보")
    if report["overclaim_candidates"]:
        for c in report["overclaim_candidates"]:
            print(f"  · ({c['count']}회) {c['phrase']}")
    else:
        print("  (임계치 이상 반복된 표현 없음)")

    print("\n[누락 정보 후보] — 상담사가 제안에 자주 보탠 표현")
    print("  → 정책 문서·프롬프트 보강 후보")
    if report["missing_info_candidates"]:
        for c in report["missing_info_candidates"]:
            print(f"  · ({c['count']}회) {c['phrase']}")
    else:
        print("  (임계치 이상 반복된 표현 없음)")

    if report["rejected_samples"]:
        print(f"\n[무시된 제안 샘플] — 방향 자체가 틀린 케이스 ({a['rejected']}건 중 일부)")
        for r in report["rejected_samples"]:
            print(f"  · [턴{r['turn']}] {r['suggested'][:80]}")

    if llm_result and llm_result.get("error_cases"):
        print("\n" + "=" * 60)
        print("[LLM 군집화] 반복 오류 유형 + 가드레일 규칙 후보")
        print("=" * 60)
        for i, ec in enumerate(llm_result["error_cases"], 1):
            print(f"\n{i}. {ec['name']}")
            print(f"   설명: {ec['description']}")
            print(f"   제안 규칙: {ec['proposed_rule']}")
            kws = ec.get("candidate_keywords")
            if kws:
                print(f"   키워드 후보: {', '.join(kws)}")


def main():
    ap = argparse.ArgumentParser(description="HITL 피드백 로그 → 오류 케이스 후보 발굴")
    ap.add_argument("--input", type=Path, default=DEFAULT_LOG, help="JSONL 로그 경로")
    ap.add_argument("--supabase", action="store_true", help="Supabase에서 조회")
    ap.add_argument("--limit", type=int, default=1000, help="Supabase 조회 상한")
    ap.add_argument("--min-count", type=int, default=2, help="후보로 볼 최소 반복 횟수")
    ap.add_argument("--top-n", type=int, default=15, help="표시할 상위 후보 수")
    ap.add_argument("--llm", action="store_true", help="OpenAI로 오류 유형 군집화 + 규칙 제안")
    ap.add_argument("--model", default=os.getenv("LLM_MODEL", "gpt-4o"), help="LLM 모델")
    ap.add_argument("--json", type=Path, help="머신용 JSON 리포트 저장 경로")
    args = ap.parse_args()

    if args.supabase:
        entries = load_from_supabase(args.limit)
        source = "Supabase"
    else:
        entries = load_from_jsonl(args.input)
        source = str(args.input)

    entries = [e for e in entries if e.get("action") in VALID_ACTIONS]
    print(f"소스: {source} — {len(entries)}건 로드\n")

    report = analyze(entries, min_count=args.min_count, top_n=args.top_n)

    llm_result = None
    if args.llm and report["total"] > 0:
        try:
            llm_result = llm_cluster(report, args.model)
        except Exception as e:
            print(f"[llm] 군집화 실패(건너뜀): {e}\n", file=sys.stderr)

    print_report(report, llm_result)

    if args.json:
        out = {k: v for k, v in report.items() if k != "edited_pairs"}
        out["edited_pairs_count"] = len(report["edited_pairs"])
        if llm_result:
            out["llm_error_cases"] = llm_result.get("error_cases", [])
        args.json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"\n📄 JSON 리포트 저장: {args.json}")


if __name__ == "__main__":
    main()
