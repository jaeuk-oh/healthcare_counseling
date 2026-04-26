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
          <span className="flex h-2.5 w-2.5 rounded-full bg-green-400" />
          <h2 className="text-base font-semibold text-gray-800">피상담자 채팅</h2>
        </div>
        <p className="mt-0.5 text-xs text-gray-500">
          시민의 상담 내용을 입력하거나 붙여넣으세요.
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
        {messages.length === 0 && (
          <div className="flex h-full items-center justify-center text-center text-gray-400">
            <p className="text-sm">상담 내용을 입력하면 대화가 시작됩니다.</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "rounded-br-sm bg-blue-500 text-white"
                  : "rounded-bl-sm bg-gray-100 text-gray-800"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-gray-100 p-4">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="예: 암 진단받았고 소득이 없어요. 의료비 지원 받을 수 있나요?"
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
