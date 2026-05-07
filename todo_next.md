# Todo Next

## 대기 중 (직접 작업 필요)

- [ ] Supabase 대시보드에서 테이블 생성 SQL 실행

```sql
CREATE TABLE sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  started_at TIMESTAMPTZ DEFAULT NOW(),
  ended_at TIMESTAMPTZ,
  scenario TEXT,
  personality TEXT,
  total_turns INTEGER DEFAULT 0,
  prompt_tokens INTEGER DEFAULT 0,
  completion_tokens INTEGER DEFAULT 0,
  total_tokens INTEGER DEFAULT 0,
  final_checklist JSONB
);

CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
  turn_index INTEGER NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

- [ ] `.env`에 값 입력
  - `SUPABASE_URL=`
  - `SUPABASE_ANON_KEY=`

- [ ] `pip install supabase` 실행

---

## 다음 단계 (암묵지 파이프라인)

- [ ] 누적 대화 데이터 패턴 분석 — 세션이 N개 쌓이면 LLM이 공통 패턴·실패 케이스 추출
- [ ] 시스템 프롬프트 개선안 자동 생성 (diff 형태)
- [ ] 관리자 승인 후 프롬프트 적용 흐름 구현
