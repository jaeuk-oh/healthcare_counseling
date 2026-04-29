"use client";

import { useState, useCallback } from "react";
import type { ChatMessage, PolicyRecommendation, ChatResponse } from "@/types";
import CalleePanel from "@/components/CalleePanel";
import RecommendationPanel from "@/components/RecommendationPanel";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [scenario, setScenario] = useState("");
  const [started, setStarted] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [counselorInput, setCounselorInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [recommendations, setRecommendations] = useState<PolicyRecommendation[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const callChat = useCallback(
    async (currentMessages: ChatMessage[]) => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ scenario, messages: currentMessages }),
        });
        if (!res.ok) throw new Error(`서버 오류 (${res.status})`);
        const data: ChatResponse = await res.json();
        setMessages((prev) => [...prev, { role: "citizen", content: data.citizen_message }]);
        setRecommendations(data.recommendations);
      } catch (err) {
        setError(err instanceof Error ? err.message : "알 수 없는 오류가 발생했습니다.");
      } finally {
        setLoading(false);
      }
    },
    [scenario]
  );

  const startConsultation = useCallback(async () => {
    if (!scenario.trim() || loading) return;
    setStarted(true);
    setMessages([]);
    setRecommendations(null);
    await callChat([]);
  }, [scenario, loading, callChat]);

  const sendCounselorMessage = useCallback(async () => {
    const content = counselorInput.trim();
    if (!content || loading) return;
    const updated: ChatMessage[] = [...messages, { role: "counselor", content }];
    setMessages(updated);
    setCounselorInput("");
    await callChat(updated);
  }, [counselorInput, loading, messages, callChat]);

  const reset = useCallback(() => {
    setStarted(false);
    setScenario("");
    setMessages([]);
    setCounselorInput("");
    setRecommendations(null);
    setError(null);
  }, []);

  if (!started) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50">
        <div className="w-full max-w-lg rounded-2xl bg-white p-8 shadow-sm ring-1 ring-gray-200">
          <h1 className="text-xl font-bold text-gray-900">보건소 의료비 지원 상담 AI</h1>
          <p className="mt-1 text-sm text-gray-500">
            시민 시나리오를 입력하면 AI가 상담 전화를 걸어옵니다.
          </p>
          <div className="mt-6">
            <label className="text-sm font-medium text-gray-700">시민 상황</label>
            <textarea
              value={scenario}
              onChange={(e) => setScenario(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  startConsultation();
                }
              }}
              placeholder="예: 50대 남성, 위암 진단, 건강보험 가입, 소득 없음"
              rows={4}
              className="mt-1.5 w-full resize-none rounded-xl border border-gray-200 bg-gray-50 px-3 py-2.5 text-sm outline-none transition focus:border-blue-400 focus:bg-white focus:ring-2 focus:ring-blue-100"
            />
          </div>
          <button
            onClick={startConsultation}
            disabled={!scenario.trim() || loading}
            className="mt-4 w-full rounded-xl bg-blue-500 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-600 disabled:opacity-40"
          >
            {loading ? "연결 중…" : "상담 시작"}
          </button>
          {error && (
            <p className="mt-3 text-xs text-red-500">{error}</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col">
      <header className="shrink-0 border-b border-gray-200 bg-white px-6 py-3 shadow-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-gray-900">보건소 의료비 지원 상담 AI</h1>
            <p className="mt-0.5 max-w-xl truncate text-xs text-gray-500">
              시민 상황: {scenario}
            </p>
          </div>
          <button
            onClick={reset}
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
          <div className="flex-1">
            <RecommendationPanel recommendations={recommendations} loading={loading} />
          </div>
        </div>
      </main>

      {error && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 rounded-xl bg-red-50 px-4 py-2.5 text-sm text-red-700 shadow-lg ring-1 ring-red-200">
          {error}
        </div>
      )}
    </div>
  );
}
