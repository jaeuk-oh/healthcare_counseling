"use client";

import { useState } from "react";
import type { PolicyRecommendation } from "@/types";

interface PolicyCardProps {
  recommendation: PolicyRecommendation;
}

export default function PolicyCard({ recommendation }: PolicyCardProps) {
  const [open, setOpen] = useState(false);
  const { policy_name, applicable, eligibility_reasoning, source_excerpts } = recommendation;

  return (
    <div
      className={`rounded-xl border-2 p-4 transition-colors ${
        applicable
          ? "border-green-400 bg-green-50"
          : "border-gray-200 bg-white opacity-60"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
              applicable ? "bg-green-500 text-white" : "bg-gray-300 text-gray-600"
            }`}
          >
            {applicable ? "✓" : "✗"}
          </span>
          <span className="font-semibold text-gray-800">{policy_name}</span>
        </div>
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
            applicable
              ? "bg-green-100 text-green-700"
              : "bg-gray-100 text-gray-500"
          }`}
        >
          {applicable ? "해당" : "미해당"}
        </span>
      </div>

      <p className="mt-2 text-sm leading-relaxed text-gray-700">
        {eligibility_reasoning}
      </p>

      {source_excerpts.length > 0 && (
        <div className="mt-3">
          <button
            onClick={() => setOpen((v) => !v)}
            className="flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-800"
          >
            <span>{open ? "▾" : "▸"}</span>
            근거 조항 {source_excerpts.length}건
          </button>

          {open && (
            <ul className="mt-2 space-y-2">
              {source_excerpts.map((ex, i) => (
                <li key={i} className="rounded-lg bg-white px-3 py-2 text-xs shadow-sm ring-1 ring-gray-200">
                  <span className="font-medium text-blue-700">[{ex.article}]</span>{" "}
                  <span className="text-gray-600">{ex.text}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
