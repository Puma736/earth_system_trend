"use client";

import { useEffect } from "react";
import { GeoJSON, MapContainer, Rectangle, TileLayer, Tooltip, useMap } from "react-leaflet";
import type { PathOptions } from "leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { CHART } from "@/components/chart-kit";
import { departments } from "@/lib/bolivia";
import { formatCount, formatLat, formatLon } from "@/lib/format";
import { binFor } from "@/lib/hotspot-scale";
import type { BBox, HotspotCell } from "@/lib/types";

export interface GeoMapProps {
  bbox: BBox | null;
  cells: HotspotCell[];
  cellDeg: number;
  /** Por ejemplo "Aug–Sep 2024": se muestra en el tooltip de cada celda. */
  period: string;
  label: string;
}

const departmentStyle: PathOptions = {
  color: CHART.text,
  weight: 1,
  opacity: 0.45,
  fill: false,
};

const regionStyle: PathOptions = {
  color: CHART.region,
  weight: 2,
  dashArray: "6 5",
  fill: false,
};

export function GeoMap({ bbox, cells, cellDeg, period, label }: GeoMapProps) {
  const half = cellDeg / 2;
  return (
    <div className="geo-map-frame" role="region" aria-label={label}>
      <MapContainer center={[-16.3, -64.7]} zoom={5} scrollWheelZoom={false} className="geo-map" preferCanvas>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />
        <FitRegion bbox={bbox} />
        {cells.map((cell) => (
          <Rectangle
            key={`${cell.lat}:${cell.lon}`}
            bounds={[
              [cell.lat - half, cell.lon - half],
              [cell.lat + half, cell.lon + half],
            ]}
            pathOptions={{
              color: CHART.surface,
              weight: 1,
              opacity: 0.6,
              fillColor: binFor(cell.count).color,
              fillOpacity: 0.88,
            }}
          >
            <Tooltip sticky className="map-tooltip">
              <strong>{formatCount(cell.count)}</strong> hotspots · {period}
              <br />
              Cell centered at {formatLat(cell.lat)}, {formatLon(cell.lon)}
            </Tooltip>
          </Rectangle>
        ))}
        <GeoJSON data={departments} style={departmentStyle} interactive={false} />
        {bbox ? (
          <Rectangle
            bounds={[
              [bbox.south, bbox.west],
              [bbox.north, bbox.east],
            ]}
            pathOptions={regionStyle}
            interactive={false}
          />
        ) : null}
      </MapContainer>
    </div>
  );
}

/** Encuadra la región cuando cambia y mantiene el tamaño del mapa al día. */
function FitRegion({ bbox }: { bbox: BBox | null }) {
  const map = useMap();
  const boundsKey = bbox ? `${bbox.west},${bbox.south},${bbox.east},${bbox.north}` : "";

  useEffect(() => {
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(map.getContainer());
    return () => observer.disconnect();
  }, [map]);

  useEffect(() => {
    if (!bbox) return;
    const bounds = L.latLngBounds([bbox.south, bbox.west], [bbox.north, bbox.east]);
    let done = false;
    const apply = () => {
      if (done) return;
      map.invalidateSize();
      const size = map.getSize();
      // El contenedor puede no tener tamaño todavía (carga diferida o layout en curso).
      if (size.x < 50 || size.y < 50) return;
      done = true;
      map.fitBounds(bounds, { padding: [16, 16], animate: false });
    };
    apply();
    const frame = requestAnimationFrame(apply);
    const timers = [150, 500].map((delay) => window.setTimeout(apply, delay));
    return () => {
      done = true;
      cancelAnimationFrame(frame);
      timers.forEach((timer) => window.clearTimeout(timer));
    };
    // boundsKey resume bbox: solo se vuelve a encuadrar si cambia la región.
  }, [boundsKey, map]);

  return null;
}
