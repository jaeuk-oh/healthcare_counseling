"use client";

import type { PolicyChecklist, PolicyCriterion } from "@/types";

interface PolicyCardProps {
  checklist: PolicyChecklist;
}

const isDecisive = (c: PolicyCriterion) => c.decisive !== false;

function criterionIcon(c: PolicyCriterion) {
  if (c.met === true) return { icon: "✓", cls: "bg-green-500 text-white" };
  if (c.met === false) {
    // 분기 판별 항목의 false 는 탈락이 아니다. ✗ 로 그리면 상담사가 오독한다.
    return isDecisive(c)
      ? { icon: "✗", cls: "bg-red-400 text-white" }
      : { icon: "→", cls: "bg-blue-100 text-blue-600" };
  }
  return { icon: "·", cls: "bg-gray-200 text-gray-500" };
}

export default function PolicyCard({ checklist }: PolicyCardProps) {
  const { name, criteria } = checklist;

  const phoneCriteria = criteria.filter((c) => c.confirmable_by !== "visit");
  const visitCriteria = criteria.filter((c) => c.confirmable_by === "visit");

  // 분기 판별 항목(decisive === false)은 카드 배지 판정에서 제외한다.
  // 성인암의 '보험 유형 확인'은 건강보험 가입자일 때 met=false 가 되는데, 이걸 부적격으로
  // 세면 조건을 충족하는 건보 가입자에게 '해당 없음'(빨강)이 뜬다. 지원을 놓치는 쪽의
  // 피해가 헛걸음보다 크다는 것이 이 프로젝트의 전제이므로, 그 방향의 오표시를 막는다.
  const decisivePhoneCriteria = phoneCriteria.filter(isDecisive);

  const allPhoneMet =
    decisivePhoneCriteria.length > 0 && decisivePhoneCriteria.every((c) => c.met === true);
  const anyPhoneFalse = decisivePhoneCriteria.some((c) => c.met === false);

  const cardCls = allPhoneMet
    ? "border-green-400 bg-green-50"
    : anyPhoneFalse
    ? "border-red-200 bg-red-50 opacity-70"
    : "border-gray-200 bg-white";

  const badge = allPhoneMet
    ? { label: "내방 안내 가능", cls: "bg-green-100 text-green-700" }
    : anyPhoneFalse
    ? { label: "해당 없음", cls: "bg-red-100 text-red-600" }
    : { label: "확인 중", cls: "bg-gray-100 text-gray-500" };

  return (
    <div className={`rounded-xl border-2 p-4 transition-colors ${cardCls}`}>
      <div className="flex items-center justify-between gap-2">
        <span className="font-semibold text-gray-800">{name}</span>
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${badge.cls}`}>
          {badge.label}
        </span>
      </div>

      {phoneCriteria.length > 0 && (
        <div className="mt-3">
          <p className="mb-1.5 text-xs font-medium text-gray-400 uppercase tracking-wide">전화 확인</p>
          <ul className="space-y-1.5">
            {phoneCriteria.map((c) => {
              const { icon, cls } = criterionIcon(c);
              return (
                <li key={c.label} className="flex items-start gap-2 text-sm">
                  <span
                    className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-xs font-bold ${cls}`}
                  >
                    {icon}
                  </span>
                  <span
                    className={
                      c.met === false && isDecisive(c)
                        ? "text-gray-400 line-through"
                        : "text-gray-700"
                    }
                  >
                    {c.label}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {visitCriteria.length > 0 && (
        <div className="mt-3 border-t border-gray-100 pt-3">
          <p className="mb-1.5 text-xs font-medium text-blue-400 uppercase tracking-wide">📄 내방 시 서류 확인</p>
          <ul className="space-y-1.5">
            {visitCriteria.map((c) => (
              <li key={c.label} className="flex items-start gap-2 text-sm text-gray-400">
                <span className="mt-0.5 shrink-0 text-blue-300 text-xs">―</span>
                <span>{c.label}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
