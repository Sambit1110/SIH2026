"use client";

import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { RelayHop } from "@/lib/api";

const RISK_COLOR: Record<string, string> = {
  MALICIOUS: "#fb3d5c",
  SUSPICIOUS: "#facc15",
  CLEAN: "#34d399",
  UNKNOWN: "#60a5fa",
};

// MapLibre's own demo-tiles style: keyless, explicitly intended for demo/dev
// use (unlike hammering tile.openstreetmap.org directly, which is rate
// limited for non-browser/bulk traffic and an unreliable choice for a live
// demo). If it's ever unreachable, markers still render on the plain
// background below -- the map remains functionally useful either way.
const STYLE_URL = "https://demotiles.maplibre.org/style.json";

export function GeoMap({ hops }: { hops: RelayHop[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  const geoHops = hops.filter((h) => h.geo && h.geo.lat != null && h.geo.lon != null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: STYLE_URL,
      center: [20, 20],
      zoom: 1.3,
      attributionControl: false,
    });
    map.on("error", (e) => console.warn("Map style/tile error (non-fatal, markers still render):", e.error?.message));
    map.addControl(new maplibregl.AttributionControl({ compact: true }));
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || geoHops.length === 0) return;

    const markers: maplibregl.Marker[] = [];
    const bounds = new maplibregl.LngLatBounds();

    geoHops.forEach((hop) => {
      const lon = hop.geo!.lon as number;
      const lat = hop.geo!.lat as number;
      const color = RISK_COLOR[hop.geo!.reputation] ?? RISK_COLOR.UNKNOWN;

      const el = document.createElement("div");
      el.style.width = "16px";
      el.style.height = "16px";
      el.style.borderRadius = "50%";
      el.style.background = color;
      el.style.border = "2px solid rgba(255,255,255,0.85)";
      el.style.boxShadow = `0 0 0 4px ${color}33`;
      el.style.cursor = "pointer";

      const popup = new maplibregl.Popup({ offset: 14, closeButton: false }).setHTML(`
        <div style="font-family: ui-sans-serif; font-size: 12px; min-width:180px">
          <div style="font-weight:600; margin-bottom:4px;">Hop ${hop.sequence} · ${hop.ip ?? "unknown"}</div>
          <div>${hop.geo!.city}, ${hop.geo!.country}</div>
          <div style="color:#92a0b4;">${hop.geo!.isp}</div>
          <div style="color:#92a0b4; margin-top:4px;">Source: ${hop.geo!.source}</div>
        </div>
      `);

      const marker = new maplibregl.Marker({ element: el }).setLngLat([lon, lat]).setPopup(popup).addTo(map);
      markers.push(marker);
      bounds.extend([lon, lat]);
    });

    if (geoHops.length === 1) {
      map.jumpTo({ center: bounds.getCenter(), zoom: 4 });
    } else if (geoHops.length > 1) {
      map.fitBounds(bounds, { padding: 60, maxZoom: 5 });
    }

    return () => {
      markers.forEach((m) => m.remove());
    };
  }, [geoHops]);

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full rounded-lg overflow-hidden" />
      <div className="absolute bottom-2 left-2 right-2 rounded-md bg-[var(--bg-elevated)]/90 border border-[var(--border)] px-3 py-1.5 text-[10px] text-[var(--text-muted)] backdrop-blur">
        Markers show <strong className="text-[var(--text)]">observed infrastructure location</strong> only —
        not a physical attacker location.
      </div>
    </div>
  );
}
