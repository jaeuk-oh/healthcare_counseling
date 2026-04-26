"use client";

import { useState, useCallback } from "react";
import type { ChatMessage, PolicyRecommendation, QueryResponse } from "@/types";
import CalleePanel from "@/components/CalleePanel";
import RecommendationPanel from "@/components/RecommendationPanel";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [recommendations, setRecommendations] = useState<PolicyRecommendation[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(async () => {
    const query = input.trim();
    if (!query || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });

      if (!res.ok) {
        const detail = await res.text();
        throw new Error(`서버 오류 (${res.status}): ${detail}`);
      }

      const data: QueryResponse = await res.json();
      setRecommendations(data.recommendations);

      const applicable = data.recommendations.filter((r) => r.applicable).map((r) => r.policy_name);
      const summary =
        applicable.length > 0
          ? `${applicable.join(", ")} 지원 가능성이 있습니다.`
          : "현재 입력하신 내용으로는 해당되는 지원 정책을 찾지 못했습니다.";

      setMessages((prev) => [...prev, { role: "assistant", content: summary }]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "알 수 없는 오류가 발생했습니다.";
      setError(msg);
      setMessages((prev) => [...prev, { role: "assistant", content: `오류: ${msg}` }]);
    } finally {
      setLoading(false);
    }
  }, [input, loading]);

  return (
    <div className="flex h-screen flex-col">
      <header className="shrink-0 border-b border-gray-200 bg-white px-6 py-3 shadow-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-gray-900">
              보건소 의료비 지원 상담 AI
            </h1>
            <p className="text-xs text-gray-500">RAG 기반 의료비 지원 정책 안내 시스템</p>
          </div>
          <a
            href={`${API_BASE}/health`}
            target="_blank"
            rel="noreferrer"
            className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs text-gray-500 hover:bg-gray-50"
          >
            API 상태 확인
          </a>
        </div>
      </header>

      <main className="flex flex-1 overflow-hidden">
        <div className="mx-auto flex w-full max-w-7xl gap-4 p-4">
          <div className="flex-1">
            <CalleePanel
              messages={messages}
              input={input}
              loading={loading}
              onInputChange={setInput}
              onSubmit={handleSubmit}
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
