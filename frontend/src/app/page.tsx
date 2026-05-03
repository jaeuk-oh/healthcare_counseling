"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import type { ChatMessage, PolicyChecklist, ChatResponse, ClassifyResponse, TokenUsage } from "@/types";
import CalleePanel from "@/components/CalleePanel";
import RecommendationPanel from "@/components/RecommendationPanel";
import HospitalSearchPanel from "@/components/HospitalSearchPanel";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const DEFAULT_SCENARIO = "50대 남성, 경기도 하남시 미사강변대로 200 미사리버하임 101동 1502호 거주, 위암 진단, 의료급여 수급자, 치료비 부담으로 지원 문의";

const PERSONALITY_TYPES = [
  "말을 더듬고 문장을 자주 중간에 끊음",
  "매우 짧고 단답식으로만 대답함",
  "짜증이 섞인 말투, 빨리 처리해달라는 태도",
  "모든 걸 다 해달라는 민원형, 상세한 설명 요구",
  "표준적인 말투 (특별한 특징 없음)",
];

const PRESET_SCENARIOS = [
  "50대 남성, 경기도 하남시 미사강변대로 200 미사리버하임 101동 1502호 거주, 위암 진단, 의료급여 수급자, 치료비 부담으로 지원 문의",
  "50대 여성, 경기도 하남시 위례학암로 14번길 위례자이아파트 202동 505호 거주, 건강보험 가입, 국가암검진 대상자 안내 우편을 받았는데 어디서 검진받으면 되는지 문의",
  "60대 남성, 경기도 하남시 대청로 33 하남아이파크 303동 801호 거주, 희귀질환(파브리병) 진단, 의료급여 수급자, 의료비 지원 문의",
  "40대 남성, 경기도 하남시 감일백제로 105 감일센트럴뷰 501동 1201호 거주, 건강보험 가입, 대장암 국가암검진 통보서 받고 가까운 검진기관 안내 요청",
  "40대 여성, 경기도 하남시 미사강변동로 79 미사역아이파크 201동 703호 거주, 건강보험 가입자, 2023년 유방암 진단, 치료비 부담으로 보건소 의료비 지원 문의",
];

function pickPersonality(): string {
  return PERSONALITY_TYPES[Math.floor(Math.random() * PERSONALITY_TYPES.length)];
}

function withPersonality(scenario: string): string {
  const p = pickPersonality();
  return `${scenario} [성격: ${p}]`;
}

function extractPersonality(scenario: string): string {
  const match = scenario.match(/\[성격: ([^\]]+)\]/);
  return match ? match[1] : "표준적인 말투";
}

const ZERO_USAGE: TokenUsage = { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 };

function addUsage(a: TokenUsage, b: TokenUsage): TokenUsage {
  return {
    prompt_tokens: a.prompt_tokens + b.prompt_tokens,
    completion_tokens: a.completion_tokens + b.completion_tokens,
    total_tokens: a.total_tokens + b.total_tokens,
  };
}

export default function Home() {
  const [scenario, setScenario] = useState(DEFAULT_SCENARIO);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [counselorInput, setCounselorInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [checklist, setChecklist] = useState<PolicyChecklist[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showScenarioPicker, setShowScenarioPicker] = useState(false);
  const [sessionTokens, setSessionTokens] = useState<TokenUsage>(ZERO_USAGE);
  const [showEndModal, setShowEndModal] = useState(false);
  const initialized = useRef(false);

  const callClassify = useCallback(async (activeScenario: string): Promise<ClassifyResponse> => {
    const res = await fetch(`${API_BASE}/classify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario: activeScenario }),
    });
    if (!res.ok) throw new Error(`분류 오류 (${res.status})`);
    return res.json() as Promise<ClassifyResponse>;
  }, []);

  const callChat = useCallback(
    async (currentMessages: ChatMessage[], activeScenario: string, currentChecklist: PolicyChecklist[]) => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            scenario: activeScenario,
            messages: currentMessages,
            checklist: currentChecklist,
          }),
        });
        if (!res.ok) throw new Error(`서버 오류 (${res.status})`);
        const data: ChatResponse = await res.json();
        setMessages((prev) => [...prev, { role: "citizen", content: data.citizen_message }]);
        if (data.checklist.length > 0) setChecklist(data.checklist);
        setSessionTokens((prev) => addUsage(prev, data.token_usage));
      } catch (err) {
        setError(err instanceof Error ? err.message : "알 수 없는 오류가 발생했습니다.");
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const startNew = useCallback(
    async (newScenario: string) => {
      const activeScenario = withPersonality(newScenario);
      setScenario(activeScenario);
      setMessages([]);
      setChecklist(null);
      setSessionTokens(ZERO_USAGE);
      setError(null);
      setShowScenarioPicker(false);
      setShowEndModal(false);
      setLoading(true);
      try {
        const classifyResult = await callClassify(activeScenario);
        setChecklist(classifyResult.checklist);
        setSessionTokens((prev) => addUsage(prev, classifyResult.token_usage));
        await callChat([], activeScenario, classifyResult.checklist);
      } catch (err) {
        setError(err instanceof Error ? err.message : "알 수 없는 오류가 발생했습니다.");
        setLoading(false);
      }
    },
    [callClassify, callChat]
  );

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    startNew(DEFAULT_SCENARIO);
  }, [startNew]);

  const sendCounselorMessage = useCallback(async () => {
    const content = counselorInput.trim();
    if (!content || loading) return;
    const updated: ChatMessage[] = [...messages, { role: "counselor", content }];
    setMessages(updated);
    setCounselorInput("");
    await callChat(updated, scenario, checklist ?? []);
  }, [counselorInput, loading, messages, callChat, scenario, checklist]);

  const endSession = useCallback(async () => {
    const personality = extractPersonality(scenario);
    try {
      await fetch(`${API_BASE}/session-end`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scenario,
          personality,
          turns: messages.length,
          ...sessionTokens,
        }),
      });
    } catch {
      // 로그 저장 실패는 UX에 영향 없음
    }
    setShowEndModal(true);
  }, [scenario, messages.length, sessionTokens]);

  return (
    <div className="flex h-screen flex-col">
      <header className="shrink-0 border-b border-gray-200 bg-white px-6 py-3 shadow-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-gray-900">보건소 의료비 지원 상담 AI</h1>
            <p className="mt-0.5 max-w-xl truncate text-xs text-gray-500">시민 상황: {scenario}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={endSession}
              disabled={messages.length === 0}
              className="rounded-lg border border-red-200 px-3 py-1.5 text-xs text-red-500 hover:bg-red-50 disabled:opacity-40"
            >
              상담 종료
            </button>
            <button
              onClick={() => setShowScenarioPicker(true)}
              className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs text-gray-500 hover:bg-gray-50"
            >
              새 상담
            </button>
          </div>
        </div>
      </header>

      <main className="flex flex-1 overflow-hidden">
        <div className="mx-auto flex w-full max-w-7xl gap-4 p-4">
          <div className="flex-1">
            <CalleePanel
              messages={messages}
              input={counselorInput}
              loading={loading}
              onInputChange={setCounselorInput}
              onSubmit={sendCounselorMessage}
            />
          </div>
          <div className="flex-1 overflow-y-auto space-y-4">
            <RecommendationPanel checklist={checklist} loading={loading} />
            <HospitalSearchPanel />
          </div>
        </div>
      </main>

      {error && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 rounded-xl bg-red-50 px-4 py-2.5 text-sm text-red-700 shadow-lg ring-1 ring-red-200">
          {error}
        </div>
      )}

      {showScenarioPicker && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl ring-1 ring-gray-200">
            <h2 className="text-base font-semibold text-gray-900">새 상담 시작</h2>
            <p className="mt-1 text-xs text-gray-500">프리셋을 선택하거나 직접 입력하세요.</p>
            <div className="mt-4 space-y-2">
              {PRESET_SCENARIOS.map((s) => (
                <button
                  key={s}
                  onClick={() => startNew(s)}
                  className="w-full rounded-xl border border-gray-200 px-4 py-2.5 text-left text-xs text-gray-700 hover:bg-blue-50 hover:border-blue-300"
                >
                  {s}
                </button>
              ))}
            </div>
            <textarea
              placeholder="직접 입력…"
              rows={3}
              className="mt-3 w-full resize-none rounded-xl border border-gray-200 bg-gray-50 px-3 py-2.5 text-sm outline-none focus:border-blue-400 focus:bg-white focus:ring-2 focus:ring-blue-100"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  const val = (e.target as HTMLTextAreaElement).value.trim();
                  if (val) startNew(val);
                }
              }}
            />
            <button
              onClick={() => setShowScenarioPicker(false)}
              className="mt-3 w-full rounded-xl border border-gray-200 py-2 text-sm text-gray-500 hover:bg-gray-50"
            >
              취소
            </button>
          </div>
        </div>
      )}

      {showEndModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl ring-1 ring-gray-200">
            <h2 className="text-base font-semibold text-gray-900">상담 종료 요약</h2>
            <p className="mt-1 text-xs text-gray-500">세션 로그가 저장되었습니다.</p>

            <dl className="mt-4 space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-500">총 대화</dt>
                <dd className="font-medium text-gray-900">{messages.length}턴</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">페르소나</dt>
                <dd className="font-medium text-gray-900">{extractPersonality(scenario)}</dd>
              </div>
              <div className="mt-3 rounded-xl bg-gray-50 p-3 space-y-1.5">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">토큰 사용량</p>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">입력 (Prompt)</span>
                  <span className="font-mono font-medium text-gray-800">{sessionTokens.prompt_tokens.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">출력 (Completion)</span>
                  <span className="font-mono font-medium text-gray-800">{sessionTokens.completion_tokens.toLocaleString()}</span>
                </div>
                <div className="flex justify-between border-t border-gray-200 pt-1.5 text-sm font-semibold">
                  <span className="text-gray-700">합계</span>
                  <span className="font-mono text-blue-700">{sessionTokens.total_tokens.toLocaleString()}</span>
                </div>
              </div>
            </dl>

            <div className="mt-5 flex gap-2">
              <button
                onClick={() => { setShowEndModal(false); setShowScenarioPicker(true); }}
                className="flex-1 rounded-xl bg-blue-500 py-2 text-sm font-semibold text-white hover:bg-blue-600"
              >
                새 상담 시작
              </button>
              <button
                onClick={() => setShowEndModal(false)}
                className="flex-1 rounded-xl border border-gray-200 py-2 text-sm text-gray-500 hover:bg-gray-50"
              >
                닫기
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
