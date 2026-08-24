"use client";

import { useEffect, useState } from "react";
import type { Persona } from "@/types";

interface PersonaPickerProps {
  apiBase: string;
  onSelect: (persona: Persona) => void;
}

export default function PersonaPicker({ apiBase, onSelect }: PersonaPickerProps) {
  const [personas, setPersonas] = useState<Persona[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${apiBase}/personas`)
      .then((res) => {
        if (!res.ok) throw new Error(`서버 오류 (${res.status})`);
        return res.json();
      })
      .then((data: Persona[]) => setPersonas(data))
      .catch((err) => setError(err instanceof Error ? err.message : "알 수 없는 오류가 발생했습니다."));
  }, [apiBase]);

  return (
    <div className="mx-auto flex h-full max-w-2xl flex-col items-center justify-center gap-6 p-6 text-center">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">연습할 민원 시나리오를 선택하세요</h2>
        <p className="mt-1 text-sm text-gray-500">
          AI가 아래 시나리오 중 하나의 민원인을 연기합니다. 자격 조건은 미리 알려주지 않으니
          직접 질문하며 체크리스트를 채워보세요.
        </p>
      </div>

      {error && <p className="text-sm text-red-500">{error}</p>}
      {!error && personas === null && <p className="text-sm text-gray-400">불러오는 중…</p>}

      {personas && (
        <div className="grid w-full gap-3 sm:grid-cols-2">
          {personas.map((p) => (
            <button
              key={p.id}
              onClick={() => onSelect(p)}
              className="rounded-xl border border-gray-200 bg-white p-4 text-left text-sm text-gray-700 shadow-sm transition hover:border-blue-300 hover:bg-blue-50"
            >
              <span className="block text-xs font-semibold text-blue-500">{p.id}</span>
              <span className="mt-1 block">{p.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
