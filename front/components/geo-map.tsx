"use client";

import { useEffect, useMemo, useState } from "react";
import { CircleMarker, GeoJSON, MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import type { LatLngBoundsExpression, PathOptions } from "leaflet";
import L from "leaflet";
import type { AdminFeature } from "@/lib/bolivia";
import type { Hotspot, MapCell, MapFocus, PlaceRef } from "@/lib/types";
import "leaflet/dist/leaflet.css";

const BOLIVIA_BOUNDS: LatLngBoundsExpression = [
  [-22.95, -69.65],
  [-9.68, -57.5],
];

interface Picked {
  name: string;
  valueLabel: string;
  lat: number;
  lon: number;
}

export function GeoMap({
  cells,
  hotspots,
  caption,
  province,
  department,
  place,
  focus,
}: {
  cells: MapCell[] | null;
  hotspots: Hotspot[];
  caption: string;
  province: AdminFeature | null;
  department: AdminFeature | null;
  place: PlaceRef | null;
  focus: MapFocus;
}) {
  const [picked, setPicked] = useState<Picked | null>(null);
  const magnitudes = cells?.map((cell) => Math.abs(cell.value)) ?? [];
  const maxMagnitude = Math.max(...magnitudes, 0.001);
  const placeIcon = useMemo(
    () =>
      L.divIcon({
        className: "place-marker",
        html: "<span></span>",
        iconSize: [16, 16],
        iconAnchor: [8, 8],
      }),
    [],
  );
  const hotspotIcon = useMemo(
    () =>
      L.divIcon({
        className: "hotspot-marker",
        html: "<span></span>",
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      }),
    [],
  );
  const outline = province ?? (focus.kind === "department" ? department : null);

  useEffect(() => {
    setPicked(null);
  }, [caption]);

  return (
    <div>
      <div className="geo-map-frame" role="region" aria-label={caption}>
        <MapContainer center={[-16.3, -64.7]} zoom={5} scrollWheelZoom className="geo-map">
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            maxZoom={19}
          />
          <MapViewport focus={focus} province={province} department={department} />
          {outline ? (
            <GeoJSON
              key={outline.properties.id}
              data={outline}
              style={province ? provinceStyle : departmentStyle}
            />
          ) : null}
          {cells?.map((cell) => (
            <CircleMarker
              key={cell.id}
              center={[cell.lat, cell.lon]}
              radius={8 + (Math.abs(cell.value) / maxMagnitude) * 16}
              pathOptions={cellStyle(cell)}
              eventHandlers={{
                click: () =>
                  setPicked({
                    name: cell.name,
                    valueLabel: formatAnomaly(cell.value),
                    lat: cell.lat,
                    lon: cell.lon,
                  }),
              }}
            >
              <Popup className="map-popup">
                <DetailLines
                  name={cell.name}
                  valueLabel={formatAnomaly(cell.value)}
                  lat={cell.lat}
                  lon={cell.lon}
                />
              </Popup>
            </CircleMarker>
          ))}
          {hotspots.map((hotspot, index) => (
            <Marker
              key={`${hotspot.date}-${hotspot.lat}-${hotspot.lon}-${index}`}
              position={[hotspot.lat, hotspot.lon]}
              icon={hotspotIcon}
              eventHandlers={{
                click: () =>
                  setPicked({
                    name: "Foco",
                    valueLabel: hotspot.date,
                    lat: hotspot.lat,
                    lon: hotspot.lon,
                  }),
              }}
            >
              <Popup className="map-popup">
                <DetailLines name="Foco" valueLabel={hotspot.date} lat={hotspot.lat} lon={hotspot.lon} />
              </Popup>
            </Marker>
          ))}
          {place ? (
            <Marker position={[place.lat, place.lon]} icon={placeIcon} zIndexOffset={800}>
              <Popup className="map-popup">
                <DetailLines
                  name={place.name}
                  valueLabel="lugar buscado"
                  lat={place.lat}
                  lon={place.lon}
                />
              </Popup>
            </Marker>
          ) : null}
        </MapContainer>
      </div>
      <p className="map-readout">
        {picked
          ? `Nombre: ${picked.name}. Valor: ${picked.valueLabel}. Coordenadas: ${picked.lat.toFixed(4)}, ${picked.lon.toFixed(4)}.`
          : "Haz clic en una zona o en un foco para ver nombre, valor y coordenadas."}
      </p>
    </div>
  );
}

function MapViewport({
  focus,
  province,
  department,
}: {
  focus: MapFocus;
  province: AdminFeature | null;
  department: AdminFeature | null;
}) {
  const map = useMap();
  const focusKey =
    focus.kind === "place"
      ? `place:${focus.lat.toFixed(5)}:${focus.lon.toFixed(5)}`
      : focus.kind === "bolivia"
        ? "bolivia"
        : `${focus.kind}:${focus.id}`;

  useEffect(() => {
    let done = false;
    const apply = () => {
      if (done) return;
      map.invalidateSize();
      if (map.getSize().y < 200 || map.getSize().x < 200) return;
      done = true;
      const animate = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (focus.kind === "place") {
        map.setView([focus.lat, focus.lon], 12, { animate });
        return;
      }
      const feature = focus.kind === "province" ? province : focus.kind === "department" ? department : null;
      if (feature) {
        const bounds = L.geoJSON(feature).getBounds();
        if (bounds.isValid()) {
          map.fitBounds(bounds, {
            padding: [28, 28],
            maxZoom: focus.kind === "province" ? 10 : 8,
            animate,
          });
        }
        return;
      }
      map.fitBounds(BOLIVIA_BOUNDS, { padding: [12, 12], animate });
    };
    apply();
    map.whenReady(apply);
    const frame = requestAnimationFrame(apply);
    const timers = [120, 400, 900].map((delay) => window.setTimeout(apply, delay));
    const observer = new ResizeObserver(apply);
    observer.observe(map.getContainer());
    return () => {
      done = true;
      cancelAnimationFrame(frame);
      timers.forEach((timer) => window.clearTimeout(timer));
      observer.disconnect();
    };
  }, [department, focus, focusKey, map, province]);

  return null;
}

function DetailLines({
  name,
  valueLabel,
  lat,
  lon,
}: {
  name: string;
  valueLabel: string;
  lat: number;
  lon: number;
}) {
  return (
    <div className="map-popup-body">
      <p>Nombre: {name}</p>
      <p>Valor: {valueLabel}</p>
      <p>
        Coordenadas: {lat.toFixed(4)}, {lon.toFixed(4)}
      </p>
    </div>
  );
}

function cellStyle(cell: MapCell): PathOptions {
  return {
    color: cell.selected ? "#3D4B97" : "#151722",
    weight: cell.selected ? 3 : 1,
    fillColor: cell.value >= 0 ? "#CBD931" : "#A0A0A5",
    fillOpacity: 0.9,
    className: "cell-marker",
  };
}

const provinceStyle: PathOptions = {
  color: "#CBD931",
  weight: 2.5,
  fillColor: "#3D4B97",
  fillOpacity: 0.16,
};

const departmentStyle: PathOptions = {
  color: "#A0A0A5",
  weight: 1.6,
  fillColor: "#3D4B97",
  fillOpacity: 0.08,
};

function formatAnomaly(value: number): string {
  const digits = Math.abs(value) >= 20 ? 1 : 2;
  const text = value.toFixed(digits);
  return value > 0 ? `+${text}` : text;
}
