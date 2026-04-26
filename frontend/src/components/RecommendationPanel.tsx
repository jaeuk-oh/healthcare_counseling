"use client";

import type { PolicyRecommendation } from "@/types";
import PolicyCard from "./PolicyCard";

interface RecommendationPanelProps {
  recommendations: PolicyRecommendation[] | null;
  loading: boolean;
}

export default function RecommendationPanel({ recommendations, loading }: RecommendationPanelProps) {
  const applicable = recommendations?.filter((r) => r.applicable) ?? [];
  const notApplicable = recommendations?.filter((r) => !r.applicable) ?? [];

  return (
    <div className="flex h-full flex-col rounded-2xl bg-white shadow-sm ring-1 ring-gray-200">
      <div className="border-b border-gray-100 px-5 py-4">
        <h2 className="text-base font-semibold text-gray-800">AI 지원 정책 추천</h2>
        <p className="mt-0.5 text-xs text-gray-500">
          해당 가능한 의료비 지원 제도를 안내합니다.
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4">
        {loading && (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-gray-400">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-200 border-t-blue-500" />
            <span className="text-sm">정책 검색 중…</span>
          </div>
        )}

        {!loading && recommendations === null && (
          <div className="flex h-full flex-col items-center justify-center text-center text-gray-400">
            <span className="text-4xl">🏥</span>
            <p className="mt-3 text-sm">
              왼쪽 패널에서 상담 내용을 입력하면
              <br />
              관련 지원 정책이 여기에 표시됩니다.
            </p>
          </div>
        )}

        {!loading && recommendations !== null && (
          <div className="space-y-3">
            {applicable.length > 0 && (
              <>
                <p className="text-xs font-semibold uppercase tracking-wide text-green-600">
                  해당 정책 ({applicable.length})
                </p>
                {applicable.map((r) => (
                  <PolicyCard key={r.policy_name} recommendation={r} />
                ))}
              </>
            )}

            {notApplicable.length > 0 && (
              <>
                <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-gray-400">
                  미해당 정책 ({notApplicable.length})
                </p>
                {notApplicable.map((r) => (
                  <PolicyCard key={r.policy_name} recommendation={r} />
                ))}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
