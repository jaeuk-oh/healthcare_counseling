"use client";

import { useRef, useEffect } from "react";
import type { ChatMessage } from "@/types";

const SAMPLE_QUESTIONS = [
  {
    label: "국가암검진",
    questions: [
      "검진 통보서를 받았는데 어느 병원에서 받으면 되나요?",
      "대장암 검진인데 대변 검사를 집에서 하는 건가요?",
      "위암 검진인데 내시경이랑 위장조영술 둘 다 해야 하나요?",
    ],
  },
  {
    label: "소아암",
    questions: [
      "아이가 백혈병 진단을 받았는데 치료비 지원이 있나요?",
      "소득이 좀 있어도 소아암 지원이 되나요?",
      "소아암 서류는 뭘 챙겨가야 하나요?",
    ],
  },
  {
    label: "성인암",
    questions: [
      "유방암 진단받았는데 치료비 지원이 되나요?",
      "의료급여 수급자인데 위암 진단받았어요. 지원받을 수 있나요?",
      "건강보험 가입자인데 대장암 지원받을 수 있나요?",
      "2년 전에 대장암으로 지원을 받았는데 올해도 계속 받을 수 있나요?",
    ],
  },
  {
    label: "희귀질환",
    questions: [
      "희귀질환 진단받았는데 의료비 지원이 있나요?",
      "산정특례 등록을 먼저 해야 하나요?",
      "희귀질환인데 간병비도 지원이 되나요?",
    ],
  },
] as const;

interface CalleePanelProps {
  messages: ChatMessage[];
  input: string;
  loading: boolean;
  onInputChange: (value: string) => void;
  onSubmit: () => void;
  onQuickFill?: (text: string) => void;
}

export default function CalleePanel({
  messages,
  input,
  loading,
  onInputChange,
  onSubmit,
  onQuickFill,
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
        <p className="mt-0.5 text-xs text-gray-500">내 메시지는 오른쪽, 상담사 AI 답변은 왼쪽입니다.</p>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto px-5 py-4">
        {messages.length === 0 && !loading && (
          <div className="flex h-full flex-col justify-center px-1 py-4">
            <p className="mb-4 text-xs text-gray-400">자주 묻는 질문을 선택하거나 직접 입력하세요.</p>
            {SAMPLE_QUESTIONS.map((category) => (
              <div key={category.label} className="mb-4">
                <p className="mb-2 text-xs font-semibold text-gray-400">{category.label}</p>
                <div className="flex flex-wrap gap-1.5">
                  {category.questions.map((q) => (
                    <button
                      key={q}
                      onClick={() => onQuickFill?.(q)}
                      className="rounded-full border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs text-gray-600 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`flex max-w-[80%] flex-col gap-1 ${
                msg.role === "user" ? "items-end" : "items-start"
              }`}
            >
              <span className="text-xs text-gray-400">
                {msg.role === "user" ? "나" : "상담사 AI"}
              </span>
              <div
                className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "rounded-br-sm bg-blue-500 text-white"
                    : "rounded-bl-sm bg-gray-100 text-gray-800"
                }`}
              >
                {msg.content}
              </div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="flex flex-col gap-1 items-start">
              <span className="text-xs text-gray-400">상담사 AI</span>
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
            placeholder="상황을 말씀해 주세요… (예: 위암 진단을 받았는데 지원받을 수 있나요?)"
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
