"use client";

import { useState } from "react";
import type { SuggestionAction } from "@/types";

interface SuggestionCardProps {
  suggestedReply: string;
  counselorNote: string;
  onResolve: (action: SuggestionAction, finalText: string) => void;
}

/**
 * AI 제안(suggested_reply)을 상담사가 검수하는 HITL 게이트.
 * - 채택: 제안을 그대로 사용 (accepted)
 * - 수정본 사용: 편집한 문구를 사용 (edited)
 * - 무시: AI 제안을 쓰지 않음 (rejected)
 * 어떤 선택이든 /suggestion-feedback 로 기록되어 오류 발굴의 원천 데이터가 된다.
 */
export default function SuggestionCard({
  suggestedReply,
  counselorNote,
  onResolve,
}: SuggestionCardProps) {
  const [draft, setDraft] = useState(suggestedReply);
  const edited = draft.trim() !== suggestedReply.trim();

  return (
    <div className="rounded-2xl border-2 border-blue-300 bg-blue-50/60 p-4">
      <div className="flex items-center gap-2">
        <span className="rounded-full bg-blue-500 px-2 py-0.5 text-xs font-semibold text-white">
          AI 제안
        </span>
        <span className="text-xs text-gray-500">
          검수 후 시민에게 발화하세요. 처리 내역이 기록됩니다.
        </span>
      </div>

      {counselorNote && (
        <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2">
          <p className="text-xs font-semibold text-amber-700">🗒 상담사 참고 (시민 비노출)</p>
          <p className="mt-1 whitespace-pre-wrap text-xs leading-relaxed text-amber-900">
            {counselorNote}
          </p>
        </div>
      )}

      <div className="mt-3">
        <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-gray-400">
          시민에게 할 답변 (편집 가능)
        </p>
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={4}
          className="w-full resize-none rounded-xl border border-gray-200 bg-white px-3 py-2.5 text-sm leading-relaxed text-gray-800 outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
        />
        {edited && (
          <p className="mt-1 text-xs text-blue-500">제안에서 수정됨 — &lsquo;수정본 사용&rsquo;으로 발화하면 edited로 기록됩니다.</p>
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <button
          onClick={() => onResolve("accepted", suggestedReply)}
          className="rounded-xl bg-blue-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-600"
        >
          채택
        </button>
        <button
          onClick={() => onResolve("edited", draft)}
          disabled={!edited || !draft.trim()}
          className="rounded-xl border border-blue-400 px-4 py-2 text-sm font-semibold text-blue-600 transition hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-40"
        >
          수정본 사용
        </button>
        <button
          onClick={() => onResolve("rejected", draft.trim() === suggestedReply.trim() ? "" : draft)}
          className="ml-auto rounded-xl border border-gray-200 px-4 py-2 text-sm text-gray-500 transition hover:bg-gray-100"
        >
          무시
        </button>
      </div>
    </div>
  );
}
