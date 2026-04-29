"use client";

import { useRef, useEffect } from "react";
import type { ChatMessage } from "@/types";

interface CalleePanelProps {
  messages: ChatMessage[];
  input: string;
  loading: boolean;
  onInputChange: (value: string) => void;
  onSubmit: () => void;
}

export default function CalleePanel({
  messages,
  input,
  loading,
  onInputChange,
  onSubmit,
}: CalleePanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!loading && input.trim()) onSubmit();
    }
  };

  return (
    <div className="flex h-full flex-col rounded-2xl bg-white shadow-sm ring-1 ring-gray-200">
      <div className="border-b border-gray-100 px-5 py-4">
        <div className="flex items-center gap-2">
          <span className="flex h-2.5 w-2.5 animate-pulse rounded-full bg-green-400" />
          <h2 className="text-base font-semibold text-gray-800">상담 진행 중</h2>
        </div>
        <p className="mt-0.5 text-xs text-gray-500">시민의 발화는 왼쪽, 상담사(나)의 답변은 오른쪽입니다.</p>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto px-5 py-4">
        {messages.length === 0 && loading && (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-gray-400">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-200 border-t-blue-500" />
            <span className="text-sm">시민이 전화 중…</span>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "counselor" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`flex max-w-[80%] flex-col gap-1 ${
                msg.role === "counselor" ? "items-end" : "items-start"
              }`}
            >
              <span className="text-xs text-gray-400">
                {msg.role === "citizen" ? "시민" : "상담사(나)"}
              </span>
              <div
                className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                  msg.role === "counselor"
                    ? "rounded-br-sm bg-blue-500 text-white"
                    : "rounded-bl-sm bg-gray-100 text-gray-800"
                }`}
              >
                {msg.content}
              </div>
            </div>
          </div>
        ))}

        {loading && messages.length > 0 && (
          <div className="flex justify-start">
            <div className="flex flex-col gap-1 items-start">
              <span className="text-xs text-gray-400">시민</span>
              <div className="rounded-2xl rounded-bl-sm bg-gray-100 px-4 py-3">
                <div className="flex gap-1">
                  <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:0ms]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:150ms]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:300ms]" />
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div className="border-t border-gray-100 p-4">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="상담사로서 답변을 입력하세요…"
            rows={3}
            disabled={loading}
            className="flex-1 resize-none rounded-xl border border-gray-200 bg-gray-50 px-3 py-2.5 text-sm placeholder-gray-400 outline-none transition focus:border-blue-400 focus:bg-white focus:ring-2 focus:ring-blue-100 disabled:opacity-50"
          />
          <button
            onClick={onSubmit}
            disabled={loading || !input.trim()}
            className="self-end rounded-xl bg-blue-500 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading ? "…" : "전송"}
          </button>
        </div>
        <p className="mt-1.5 text-xs text-gray-400">Enter로 전송 · Shift+Enter 줄바꿈</p>
      </div>
    </div>
  );
}
