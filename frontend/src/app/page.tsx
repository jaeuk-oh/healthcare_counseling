"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import type { ChatMessage, PolicyRecommendation, Referral, ChatResponse } from "@/types";
import CalleePanel from "@/components/CalleePanel";
import RecommendationPanel from "@/components/RecommendationPanel";
import HospitalSearchPanel from "@/components/HospitalSearchPanel";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const DEFAULT_SCENARIO = "50대 남성, 경기도 하남시 미사강변대로 200 미사리버하임 101동 1502호 거주, 위암 진단, 의료급여 수급자, 치료비 부담으로 지원 문의";

const PRESET_SCENARIOS = [
  "50대 남성, 경기도 하남시 미사강변대로 200 미사리버하임 101동 1502호 거주, 위암 진단, 의료급여 수급자, 치료비 부담으로 지원 문의",
  "50대 여성, 경기도 하남시 위례학암로 14번길 위례자이아파트 202동 505호 거주, 건강보험 가입, 국가암검진 대상자 안내 우편을 받았는데 어디서 검진받으면 되는지 문의",
  "60대 남성, 경기도 하남시 대청로 33 하남아이파크 303동 801호 거주, 희귀질환(파브리병) 진단, 의료급여 수급자, 의료비 지원 문의",
  "40대 남성, 경기도 하남시 감일백제로 105 감일센트럴뷰 501동 1201호 거주, 건강보험 가입, 대장암 국가암검진 통보서 받고 가까운 검진기관 안내 요청",
  "40대 여성, 경기도 하남시 미사강변동로 79 미사역아이파크 201동 703호 거주, 건강보험 가입자, 2023년 유방암 진단, 치료비 부담으로 보건소 의료비 지원 문의",
];

export default function Home() {
  const [scenario, setScenario] = useState(DEFAULT_SCENARIO);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [counselorInput, setCounselorInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [recommendations, setRecommendations] = useState<PolicyRecommendation[] | null>(null);
  const [referral, setReferral] = useState<Referral | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showScenarioPicker, setShowScenarioPicker] = useState(false);
  const initialized = useRef(false);

  const callChat = useCallback(
    async (currentMessages: ChatMessage[], activeScenario: string) => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ scenario: activeScenario, messages: currentMessages }),
        });
        if (!res.ok) throw new Error(`서버 오류 (${res.status})`);
        const data: ChatResponse = await res.json();
        setMessages((prev) => [...prev, { role: "citizen", content: data.citizen_message }]);
        setRecommendations(data.recommendations);
        setReferral(data.referral ?? null);
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
      setScenario(newScenario);
      setMessages([]);
      setRecommendations(null);
      setReferral(null);
      setError(null);
      setShowScenarioPicker(false);
      await callChat([], newScenario);
    },
    [callChat]
  );

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    callChat([], DEFAULT_SCENARIO);
  }, [callChat]);

  const sendCounselorMessage = useCallback(async () => {
    const content = counselorInput.trim();
    if (!content || loading) return;
    const updated: ChatMessage[] = [...messages, { role: "counselor", content }];
    setMessages(updated);
    setCounselorInput("");
    await callChat(updated, scenario);
  }, [counselorInput, loading, messages, callChat, scenario]);

  return (
    <div className="flex h-screen flex-col">
      <header className="shrink-0 border-b border-gray-200 bg-white px-6 py-3 shadow-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-gray-900">보건소 의료비 지원 상담 AI</h1>
            <p className="mt-0.5 max-w-xl truncate text-xs text-gray-500">시민 상황: {scenario}</p>
          </div>
          <button
            onClick={() => setShowScenarioPicker(true)}
            className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs text-gray-500 hover:bg-gray-50"
          >
            새 상담
          </button>
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
            <RecommendationPanel recommendations={recommendations} referral={referral} loading={loading} />
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
    </div>
  );
}
