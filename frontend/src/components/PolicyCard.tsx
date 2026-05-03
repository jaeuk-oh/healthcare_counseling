"use client";

import type { PolicyChecklist } from "@/types";

interface PolicyCardProps {
  checklist: PolicyChecklist;
}

function criterionIcon(met: boolean | null) {
  if (met === true) return { icon: "✓", cls: "bg-green-500 text-white" };
  if (met === false) return { icon: "✗", cls: "bg-red-400 text-white" };
  return { icon: "·", cls: "bg-gray-200 text-gray-500" };
}

export default function PolicyCard({ checklist }: PolicyCardProps) {
  const { name, criteria } = checklist;
  const allMet = criteria.length > 0 && criteria.every((c) => c.met === true);
  const anyFalse = criteria.some((c) => c.met === false);

  const cardCls = allMet
    ? "border-green-400 bg-green-50"
    : anyFalse
    ? "border-red-200 bg-red-50 opacity-70"
    : "border-gray-200 bg-white";

  const badge = allMet
    ? { label: "지원 가능", cls: "bg-green-100 text-green-700" }
    : anyFalse
    ? { label: "지원 불가", cls: "bg-red-100 text-red-600" }
    : { label: "확인 중", cls: "bg-gray-100 text-gray-500" };

  return (
    <div className={`rounded-xl border-2 p-4 transition-colors ${cardCls}`}>
      <div className="flex items-center justify-between gap-2">
        <span className="font-semibold text-gray-800">{name}</span>
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${badge.cls}`}>
          {badge.label}
        </span>
      </div>

      <ul className="mt-3 space-y-1.5">
        {criteria.map((c) => {
          const { icon, cls } = criterionIcon(c.met);
          return (
            <li key={c.label} className="flex items-start gap-2 text-sm">
              <span
                className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-xs font-bold ${cls}`}
              >
                {icon}
              </span>
              <span className={c.met === false ? "text-gray-400 line-through" : "text-gray-700"}>
                {c.label}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
