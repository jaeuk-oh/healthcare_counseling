"use client";

import type { PolicyChecklist } from "@/types";
import PolicyCard from "./PolicyCard";

interface RecommendationPanelProps {
  checklist: PolicyChecklist[] | null;
  loading: boolean;
}

export default function RecommendationPanel({ checklist, loading }: RecommendationPanelProps) {
  return (
    <div className="flex h-full flex-col rounded-2xl bg-white shadow-sm ring-1 ring-gray-200">
      <div className="border-b border-gray-100 px-5 py-4">
        <h2 className="text-base font-semibold text-gray-800">AI 지원 정책 추천</h2>
        <p className="mt-0.5 text-xs text-gray-500">
          대화가 진행되면서 체크 항목이 하나씩 확인됩니다.
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4">
        {loading && checklist === null && (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-gray-400">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-200 border-t-blue-500" />
            <span className="text-sm">정책 분류 중…</span>
          </div>
        )}

        {!loading && checklist === null && (
          <div className="flex h-full flex-col items-center justify-center text-center text-gray-400">
            <span className="text-4xl">🏥</span>
            <p className="mt-3 text-sm">
              왼쪽 패널에서 상담 내용을 입력하면
              <br />
              관련 지원 정책이 여기에 표시됩니다.
            </p>
          </div>
        )}

        {checklist !== null && (
          <div className="space-y-3">
            {checklist.length === 0 ? (
              <p className="py-6 text-center text-sm text-gray-400">
                해당 가능한 의료비 지원 정책이 없습니다.
              </p>
            ) : (
              checklist.map((item) => (
                <PolicyCard key={item.name} checklist={item} />
              ))
            )}

            {loading && checklist.length > 0 && (
              <div className="flex items-center gap-2 pt-1 text-xs text-gray-400">
                <div className="h-3 w-3 animate-spin rounded-full border-2 border-blue-200 border-t-blue-400" />
                항목 업데이트 중…
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
