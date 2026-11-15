"use client";

import { useEffect, useMemo } from "react";
import { GeoJSON, MapContainer, TileLayer, useMap } from "react-leaflet";
import type { PathOptions } from "leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { CHART } from "@/components/chart-kit";
import { departments, featureCovers, featureHitsCell, type DepartmentFeature } from "@/lib/bolivia";
import { formatCount, formatLat, formatLon } from "@/lib/format";
import { binFor } from "@/lib/hotspot-scale";
import type { BBox, HotspotCell } from "@/lib/types";

export interface GeoMapProps {
  bbox: BBox | null;
  cells: HotspotCell[];
  cellDeg: number;
  /** Alto de la celda en grados. Si no viene, se usa cellDeg. */
  cellDegLat?: number;
  /** Ancho de la celda en grados. Si no viene, se usa cellDeg. */
  cellDegLon?: number;
  /** Por ejemplo "Aug–Sep 2024": se muestra en el tooltip de cada celda. */
  period: string;
  label: string;
  /** Provincias elegidas: relleno continuo, focos y encuadre. */
  selected?: DepartmentFeature[];
  /** Resto de provincias de la región, solo el contorno. */
  context?: DepartmentFeature[];
}

const departmentStyle: PathOptions = {
  color: CHART.text,
  weight: 1,
  opacity: 0.4,
  fill: false,
};

const contextStyle: PathOptions = {
  color: "#CBD931",
  weight: 1.75,
  opacity: 0.9,
  fill: false,
};

const territoryCase: PathOptions = {
  color: "#151722",
  weight: 7,
  opacity: 1,
  fill: false,
  lineCap: "round",
  lineJoin: "round",
};

const territoryLine: PathOptions = {
  color: "#f6f8d4",
  weight: 3.75,
  opacity: 1,
  fill: false,
  lineCap: "round",
  lineJoin: "round",
};

interface HeatTile {
  south: number;
  west: number;
  north: number;
  east: number;
  lat: number;
  lon: number;
  count: number;
  color: string;
  ink: string;
}

export function GeoMap({
  bbox,
  cells,
  cellDeg,
  cellDegLat,
  cellDegLon,
  period,
  label,
  selected = [],
  context = [],
}: GeoMapProps) {
  const dlat = cellDegLat ?? cellDeg;
  const dlon = cellDegLon ?? cellDeg;
  const focus = selected.length > 0 ? collectionBounds(selected) : bbox;
  const tiles = useMemo(() => heatTiles(cells, dlat, dlon, selected), [cells, dlat, dlon, selected]);
  const selectedKey = selected.map((feature) => feature.properties.id).join(",");
  const contextKey = context.map((feature) => feature.properties.id).join(",");
  const named = useMemo(() => (context.length === 0 ? selected : [...selected, ...context]), [context, selected]);

  return (
    <div className="geo-map-frame" role="region" aria-label={label}>
      <MapContainer center={[-16.3, -64.7]} zoom={5} scrollWheelZoom className="geo-map" preferCanvas>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />
        <OutlinePane />
        <FitRegion bbox={focus} />
        <GeoJSON data={departments} style={departmentStyle} interactive={false} />
        {context.length > 0 ? (
          <GeoJSON key={`context-${contextKey}`} data={collection(context)} style={contextStyle} pane="province-outline" interactive={false} />
        ) : null}
        <JoinedHeat tiles={tiles} provinces={selected} named={named} period={period} />
        {selected.length > 0 && selected.length <= 6 ? (
          <GeoJSON
            key={`names-${selectedKey}`}
            data={collection(selected)}
            style={{ stroke: false, fillOpacity: 0, opacity: 0 }}
            interactive={false}
            onEachFeature={(feature, layer) => {
              const name = String(feature.properties?.name ?? "");
              if (name) layer.bindTooltip(name, { permanent: true, direction: "center", className: "place-label" });
            }}
          />
        ) : null}
        {selected.length > 0 ? (
          <GeoJSON
            key={`case-${selectedKey}`}
            data={collection(selected)}
            style={territoryCase}
            pane="province-outline"
            interactive={false}
          />
        ) : null}
        {selected.length > 0 ? (
          <GeoJSON
            key={`line-${selectedKey}`}
            data={collection(selected)}
            style={territoryLine}
            pane="province-outline"
            interactive={false}
          />
        ) : null}
      </MapContainer>
    </div>
  );
}

function collection(features: DepartmentFeature[]) {
  return { type: "FeatureCollection" as const, features };
}

/**
 * Rectángulo centrado en la coordenada guardada. El borde queda a media celda.
 * No se interpola: dlat y dlon son el paso de la rejilla de origen.
 */
function heatTiles(
  cells: HotspotCell[],
  dlat: number,
  dlon: number,
  provinces: DepartmentFeature[],
): HeatTile[] {
  if (provinces.length === 0 || dlat <= 0 || dlon <= 0) return [];
  const halfLat = dlat / 2;
  const halfLon = dlon / 2;
  const tiles: HeatTile[] = [];
  for (const cell of cells) {
    if (!provinces.some((feature) => featureHitsCell(feature, cell.lat, cell.lon, dlat, dlon))) continue;
    const bin = binFor(cell.count);
    tiles.push({
      south: cell.lat - halfLat,
      west: cell.lon - halfLon,
      north: cell.lat + halfLat,
      east: cell.lon + halfLon,
      lat: cell.lat,
      lon: cell.lon,
      count: cell.count,
      color: bin.color,
      ink: bin.ink,
    });
  }
  return tiles;
}

function OutlinePane() {
  const map = useMap();
  if (!map.getPane("province-outline")) {
    const pane = map.createPane("province-outline");
    pane.style.zIndex = "450";
    pane.style.pointerEvents = "none";
  }
  return null;
}

function JoinedHeat({
  tiles,
  provinces,
  named,
  period,
}: {
  tiles: HeatTile[];
  provinces: DepartmentFeature[];
  named: DepartmentFeature[];
  period: string;
}) {
  const map = useMap();

  useEffect(() => {
    const canvas = document.createElement("canvas");
    canvas.className = "joined-heat leaflet-zoom-hide";
    canvas.style.pointerEvents = "none";
    const pane = map.getPane("overlayPane");
    if (!pane) return;
    pane.appendChild(canvas);
    const tooltip = L.tooltip({ className: "map-tooltip", sticky: true, opacity: 1 });
    let frame = 0;

    const draw = () => {
      const size = map.getSize();
      const ratio = window.devicePixelRatio || 1;
      canvas.width = Math.max(1, size.x) * ratio;
      canvas.height = Math.max(1, size.y) * ratio;
      canvas.style.width = `${size.x}px`;
      canvas.style.height = `${size.y}px`;
      L.DomUtil.setPosition(canvas, map.containerPointToLayerPoint([0, 0]));
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      ctx.clearRect(0, 0, size.x, size.y);
      ctx.save();
      if (provinces.length > 0) {
        ctx.beginPath();
        traceProvinces(ctx, provinces, map);
        ctx.clip("evenodd");
      }
      for (const tile of tiles) {
        const nw = map.latLngToContainerPoint([tile.north, tile.west]);
        const se = map.latLngToContainerPoint([tile.south, tile.east]);
        const x = Math.min(nw.x, se.x);
        const y = Math.min(nw.y, se.y);
        const w = Math.abs(se.x - nw.x);
        const h = Math.abs(se.y - nw.y);
        if (x > size.x || y > size.y || x + w < 0 || y + h < 0 || w < 1 || h < 1) continue;
        ctx.globalAlpha = 0.92;
        ctx.fillStyle = tile.color;
        ctx.fillRect(x, y, w, h);
        ctx.globalAlpha = 1;
        ctx.strokeStyle = "rgba(21, 23, 34, 0.9)";
        ctx.lineWidth = 1;
        ctx.strokeRect(x + 0.5, y + 0.5, Math.max(0, w - 1), Math.max(0, h - 1));
        if (w >= 36 && h >= 20) {
          ctx.fillStyle = tile.ink;
          ctx.font = `${Math.max(10, Math.min(13, Math.floor(h * 0.42)))}px "IBM Plex Mono", Consolas, monospace`;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(formatCount(tile.count), x + w / 2, y + h / 2);
        }
      }
      ctx.restore();
    };

    const schedule = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(draw);
    };

    const onMove = (event: L.LeafletMouseEvent) => {
      const { lat, lng } = event.latlng;
      const province = named.find((feature) => featureCovers(feature, lng, lat));
      const inside = provinces.some((feature) => featureCovers(feature, lng, lat));
      const tile = inside
        ? tiles.find((item) => lat >= item.south && lat <= item.north && lng >= item.west && lng <= item.east)
        : undefined;
      const showName = Boolean(province) && provinces.length > 6;
      if (!tile && !showName) {
        map.closeTooltip(tooltip);
        return;
      }
      const node = document.createElement("div");
      if (showName && province) {
        const name = document.createElement("strong");
        name.textContent = province.properties.name;
        node.appendChild(name);
      }
      if (tile) {
        if (node.childNodes.length > 0) node.appendChild(document.createElement("br"));
        const count = document.createElement("span");
        count.textContent = `${formatCount(tile.count)} hotspots · ${period}`;
        node.appendChild(count);
        node.appendChild(document.createElement("br"));
        const where = document.createElement("span");
        where.textContent = `Cell centered at ${formatLat(tile.lat)}, ${formatLon(tile.lon)}`;
        node.appendChild(where);
      }
      if (node.childNodes.length === 0) {
        map.closeTooltip(tooltip);
        return;
      }
      tooltip.setLatLng(event.latlng).setContent(node).addTo(map);
    };

    schedule();
    map.on("zoom zoomend moveend resize viewreset", schedule);
    map.on("mousemove", onMove);
    return () => {
      cancelAnimationFrame(frame);
      map.off("zoom zoomend moveend resize viewreset", schedule);
      map.off("mousemove", onMove);
      map.closeTooltip(tooltip);
      canvas.remove();
    };
  }, [map, named, period, provinces, tiles]);

  return null;
}

function traceProvinces(
  ctx: CanvasRenderingContext2D,
  provinces: DepartmentFeature[],
  map: L.Map,
) {
  for (const feature of provinces) {
    const polygons = feature.geometry.type === "Polygon" ? [feature.geometry.coordinates] : feature.geometry.coordinates;
    for (const rings of polygons) {
      for (const ring of rings) {
        ring.forEach((pair, index) => {
          if (!Array.isArray(pair) || typeof pair[0] !== "number" || typeof pair[1] !== "number") return;
          const point = map.latLngToContainerPoint([pair[1], pair[0]]);
          if (index === 0) ctx.moveTo(point.x, point.y);
          else ctx.lineTo(point.x, point.y);
        });
        ctx.closePath();
      }
    }
  }
}

function collectionBounds(features: DepartmentFeature[]): BBox | null {
  let west = Infinity;
  let east = -Infinity;
  let south = Infinity;
  let north = -Infinity;
  const visit = (pair: unknown) => {
    if (!Array.isArray(pair)) return;
    if (typeof pair[0] === "number" && typeof pair[1] === "number") {
      west = Math.min(west, pair[0]);
      east = Math.max(east, pair[0]);
      south = Math.min(south, pair[1]);
      north = Math.max(north, pair[1]);
      return;
    }
    pair.forEach(visit);
  };
  features.forEach((feature) => visit(feature.geometry.coordinates));
  if (!Number.isFinite(west)) return null;
  return { west, east, south, north };
}

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
  }, [boundsKey, map]);

  return null;
}
