"use client";

import { useState, useCallback } from "react";
import type { ChatMessage, PolicyChecklist, ChatResponse, TokenUsage, SuggestionAction } from "@/types";
import CalleePanel from "@/components/CalleePanel";
import RecommendationPanel from "@/components/RecommendationPanel";

interface PendingSuggestion {
  suggestedReply: string;
  counselorNote: string;
  turnIndex: number;
}


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
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sessionTokens, setSessionTokens] = useState<TokenUsage>(ZERO_USAGE);
  const [showEndModal, setShowEndModal] = useState(false);
  const [pending, setPending] = useState<PendingSuggestion | null>(null);

  const callChat = useCallback(
    async (currentMessages: ChatMessage[], currentChecklist: PolicyChecklist[], currentSessionId: string | null) => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages: currentMessages,
            checklist: currentChecklist,
            session_id: currentSessionId,
          }),
        });
        if (!res.ok) throw new Error(`서버 오류 (${res.status})`);
        const data: ChatResponse = await res.json();
        // 응답을 시민에게 직행시키지 않고, 상담사 검수 대기(제안) 상태로 둔다.
        setPending({
          suggestedReply: data.suggested_reply ?? data.counselor_message,
          counselorNote: data.counselor_note ?? "",
          turnIndex: currentMessages.length, // 상담사 발화가 들어갈 위치
        });
        if (data.checklist.length > 0) setChecklist(data.checklist);
        if (data.session_id) setSessionId(data.session_id);
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
    if (!content || loading || pending) return;
    const updated: ChatMessage[] = [...messages, { role: "user", content }];
    setMessages(updated);
    setUserInput("");
    await callChat(updated, checklist ?? [], sessionId);
  }, [userInput, loading, pending, messages, callChat, checklist, sessionId]);

  // 상담사가 AI 제안을 채택/수정/무시 → HITL 로그 기록 + 최종 발화를 대화에 반영
  const resolveSuggestion = useCallback(
    async (action: SuggestionAction, finalText: string) => {
      if (!pending) return;
      const suggested = pending.suggestedReply;
      const turnIndex = pending.turnIndex;

      // 상담사가 실제로 발화한 문구만 대화 이력(assistant)에 반영
      if (finalText.trim()) {
        setMessages((prev) => [...prev, { role: "assistant", content: finalText }]);
      }
      setPending(null);

      // 피드백 로깅 (실패해도 상담 흐름에는 영향 없음)
      try {
        await fetch(`${API_BASE}/suggestion-feedback`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sessionId,
            turn_index: turnIndex,
            suggested_reply: suggested,
            final_reply: finalText,
            action,
          }),
        });
      } catch {
        // 로깅 실패는 UX에 영향 없음
      }
    },
    [pending, sessionId]
  );

  const startNew = useCallback(() => {
    setMessages([]);
    setChecklist(null);
    setSessionId(null);
    setSessionTokens(ZERO_USAGE);
    setError(null);
    setShowEndModal(false);
    setPending(null);
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
          session_id: sessionId,
          checklist: checklist ?? [],
          ...sessionTokens,
        }),
      });
    } catch {
      // 로그 저장 실패는 UX에 영향 없음
    }
    setShowEndModal(true);
  }, [messages, sessionTokens, sessionId, checklist]);

  return (
    <div className="flex h-screen flex-col">
      <header className="shrink-0 border-b border-gray-200 bg-white px-6 py-3 shadow-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-gray-900">보건소 의료비 지원 상담사 보조 AI</h1>
            <p className="mt-0.5 text-xs text-gray-500">AI가 답변을 제안하고, 상담사가 검수해 시민에게 발화합니다.</p>
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
          <div className="flex-[2]">
            <CalleePanel
              messages={messages}
              input={userInput}
              loading={loading}
              suggestion={pending}
              onInputChange={setUserInput}
              onSubmit={sendMessage}
              onResolve={resolveSuggestion}
              onQuickFill={setUserInput}
            />
          </div>
          <div className="flex-1">
            <RecommendationPanel checklist={checklist} loading={loading} />
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
