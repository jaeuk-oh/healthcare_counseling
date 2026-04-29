"use client";

import { useEffect, useRef } from "react";
import type { Hospital } from "@/types";

interface HospitalMapProps {
  hospitals: Hospital[];
}

export default function HospitalMap({ hospitals }: HospitalMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<import("leaflet").Map | null>(null);

  useEffect(() => {
    if (!mapRef.current || hospitals.length === 0) return;

    const validHospitals = hospitals.filter((h) => h.lat && h.lng);
    if (validHospitals.length === 0) return;

    import("leaflet").then((L) => {
      // Fix default marker icons for Next.js
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      delete (L.Icon.Default.prototype as any)._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
        iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
        shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
      });

      // Remove existing map instance
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }

      const avgLat = validHospitals.reduce((s, h) => s + h.lat!, 0) / validHospitals.length;
      const avgLng = validHospitals.reduce((s, h) => s + h.lng!, 0) / validHospitals.length;

      const map = L.map(mapRef.current!, { zoomControl: true }).setView([avgLat, avgLng], 13);
      mapInstanceRef.current = map;

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap contributors",
      }).addTo(map);

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
  }, [hospitals]);

  // Load Leaflet CSS once
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

  return <div ref={mapRef} className="h-48 w-full rounded-xl overflow-hidden ring-1 ring-gray-200" />;
}
