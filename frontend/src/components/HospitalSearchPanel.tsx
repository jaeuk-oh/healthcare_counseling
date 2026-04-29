"use client";

import { useState } from "react";
import type { Hospital } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const CANCER_TYPES = ["위암", "간암", "대장암", "유방암", "자궁경부암"];

export default function HospitalSearchPanel() {
  const [address, setAddress] = useState("");
  const [cancerType, setCancerType] = useState("");
  const [hospitals, setHospitals] = useState<Hospital[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = async () => {
    if (!address.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/hospital-search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address, cancer_type: cancerType || null, top_n: 5 }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? `서버 오류 (${res.status})`);
      }
      const data = await res.json();
      setHospitals(data.hospitals);
    } catch (err) {
      setError(err instanceof Error ? err.message : "오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-3 rounded-2xl bg-white shadow-sm ring-1 ring-gray-200">
      <div className="border-b border-gray-100 px-5 py-4">
        <h2 className="text-base font-semibold text-gray-800">암검진 병원 찾기</h2>
        <p className="mt-0.5 text-xs text-gray-500">시민 주소를 입력하면 가까운 검진기관을 안내합니다.</p>
      </div>

      <div className="px-5 py-4 space-y-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && search()}
            placeholder="예: 하남시 미사동"
            className="flex-1 rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-sm outline-none transition focus:border-blue-400 focus:bg-white focus:ring-2 focus:ring-blue-100"
          />
          <select
            value={cancerType}
            onChange={(e) => setCancerType(e.target.value)}
            className="rounded-xl border border-gray-200 bg-gray-50 px-2 py-2 text-sm outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
          >
            <option value="">전체 암종</option>
            {CANCER_TYPES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        <button
          onClick={search}
          disabled={!address.trim() || loading}
          className="w-full rounded-xl bg-blue-500 py-2 text-sm font-semibold text-white transition hover:bg-blue-600 disabled:opacity-40"
        >
          {loading ? "검색 중…" : "검진기관 검색"}
        </button>

        {error && <p className="text-xs text-red-500">{error}</p>}

        {hospitals !== null && (
          <div className="space-y-2 pt-1">
            {hospitals.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-4">해당 조건의 병원이 없습니다.</p>
            ) : (
              hospitals.map((h) => (
                <div key={h.name} className="rounded-xl border border-gray-100 bg-gray-50 px-4 py-3">
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-sm font-medium text-gray-900">{h.name}</span>
                    {h.distance_km != null && (
                      <span className="shrink-0 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
                        {h.distance_km} km
                      </span>
                    )}
                  </div>
                  <a
                    href={`tel:${h.phone}`}
                    className="mt-0.5 block text-xs font-semibold text-blue-600 hover:underline"
                  >
                    {h.phone}
                  </a>
                  <p className="mt-1 text-xs text-gray-500">{h.cancers.join(" · ")}</p>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
