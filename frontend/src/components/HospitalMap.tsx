"use client";

import { useEffect, useRef } from "react";
import type { Hospital, HospitalOrigin } from "@/types";

interface HospitalMapProps {
  hospitals: Hospital[];
  origin?: HospitalOrigin | null;
}

export default function HospitalMap({ hospitals, origin }: HospitalMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<import("leaflet").Map | null>(null);

  useEffect(() => {
    if (!mapRef.current || hospitals.length === 0) return;

    const validHospitals = hospitals.filter((h) => h.lat && h.lng);
    if (validHospitals.length === 0) return;

    import("leaflet").then((L) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      delete (L.Icon.Default.prototype as any)._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
        iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
        shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
      });

      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }

      // Center on origin if available, otherwise average of hospitals
      const centerLat = origin?.lat ?? validHospitals.reduce((s, h) => s + h.lat!, 0) / validHospitals.length;
      const centerLng = origin?.lng ?? validHospitals.reduce((s, h) => s + h.lng!, 0) / validHospitals.length;

      const map = L.map(mapRef.current!, { zoomControl: true }).setView([centerLat, centerLng], 13);
      mapInstanceRef.current = map;

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap contributors",
      }).addTo(map);

      // Citizen location marker (red star)
      if (origin) {
        const originIcon = L.divIcon({
          className: "",
          html: `<div style="background:#ef4444;color:white;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.5)">★</div>`,
          iconSize: [28, 28],
          iconAnchor: [14, 14],
        });
        L.marker([origin.lat, origin.lng], { icon: originIcon })
          .addTo(map)
          .bindPopup("<b>시민 위치</b>");
      }

      // Hospital markers (blue numbered)
      validHospitals.forEach((h, i) => {
        const icon = L.divIcon({
          className: "",
          html: `<div style="background:#3b82f6;color:white;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:bold;border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.4)">${i + 1}</div>`,
          iconSize: [24, 24],
          iconAnchor: [12, 12],
        });
        L.marker([h.lat!, h.lng!], { icon })
          .addTo(map)
          .bindPopup(`<b>${h.name}</b><br/>${h.phone}${h.distance_km != null ? `<br/>${h.distance_km}km` : ""}`);
      });
    });

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [hospitals, origin]);

  useEffect(() => {
    const id = "leaflet-css";
    if (!document.getElementById(id)) {
      const link = document.createElement("link");
      link.id = id;
      link.rel = "stylesheet";
      link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
      document.head.appendChild(link);
    }
  }, []);

  return (
    <div className="space-y-1">
      <div ref={mapRef} className="h-52 w-full rounded-xl overflow-hidden ring-1 ring-gray-200" />
      <div className="flex items-center gap-3 px-1 text-xs text-gray-400">
        <span><span style={{color:"#ef4444"}}>★</span> 시민 위치</span>
        <span><span style={{color:"#3b82f6"}}>●</span> 검진기관</span>
      </div>
    </div>
  );
}
