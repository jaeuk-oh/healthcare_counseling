"use client";

import { useState, useCallback } from "react";
import type { ChatMessage, PolicyChecklist, ChatResponse, TokenUsage } from "@/types";
import CalleePanel from "@/components/CalleePanel";
import RecommendationPanel from "@/components/RecommendationPanel";
import HospitalSearchPanel from "@/components/HospitalSearchPanel";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const ZERO_USAGE: TokenUsage = { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 };

function addUsage(a: TokenUsage, b: TokenUsage): TokenUsage {
  return {
    prompt_tokens: a.prompt_tokens + b.prompt_tokens,
    completion_tokens: a.completion_tokens + b.completion_tokens,
    total_tokens: a.total_tokens + b.total_tokens,
  };
}

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [userInput, setUserInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [checklist, setChecklist] = useState<PolicyChecklist[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sessionTokens, setSessionTokens] = useState<TokenUsage>(ZERO_USAGE);
  const [showEndModal, setShowEndModal] = useState(false);

  const callChat = useCallback(
    async (currentMessages: ChatMessage[], currentChecklist: PolicyChecklist[]) => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages: currentMessages,
            checklist: currentChecklist,
          }),
        });
        if (!res.ok) throw new Error(`서버 오류 (${res.status})`);
        const data: ChatResponse = await res.json();
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.counselor_message },
        ]);
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

  const sendMessage = useCallback(async () => {
    const content = userInput.trim();
    if (!content || loading) return;
    const updated: ChatMessage[] = [...messages, { role: "user", content }];
    setMessages(updated);
    setUserInput("");
    await callChat(updated, checklist ?? []);
  }, [userInput, loading, messages, callChat, checklist]);

  const startNew = useCallback(() => {
    setMessages([]);
    setChecklist(null);
    setSessionTokens(ZERO_USAGE);
    setError(null);
    setShowEndModal(false);
  }, []);

  const endSession = useCallback(async () => {
    try {
      await fetch(`${API_BASE}/session-end`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scenario: messages[0]?.content ?? "",
          personality: "해당없음",
          turns: messages.length,
          ...sessionTokens,
        }),
      });
    } catch {
      // 로그 저장 실패는 UX에 영향 없음
    }
    setShowEndModal(true);
  }, [messages, sessionTokens]);

  return (
    <div className="flex h-screen flex-col">
      <header className="shrink-0 border-b border-gray-200 bg-white px-6 py-3 shadow-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-gray-900">보건소 의료비 지원 상담 AI</h1>
            <p className="mt-0.5 text-xs text-gray-500">상황을 입력하시면 지원 가능한 제도를 안내해 드립니다.</p>
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
              onClick={startNew}
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
              input={userInput}
              loading={loading}
              onInputChange={setUserInput}
              onSubmit={sendMessage}
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
                onClick={startNew}
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
