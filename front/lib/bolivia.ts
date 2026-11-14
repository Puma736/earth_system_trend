import rawCollection from "@/data/bolivia-admin.json";
import type { AdminRef } from "./types";

export type LngLat = [number, number];
export type LinearRing = LngLat[];

export interface PolygonGeometry {
  type: "Polygon";
  coordinates: LinearRing[];
}

export interface MultiPolygonGeometry {
  type: "MultiPolygon";
  coordinates: LinearRing[][];
}

export type AdminGeometry = PolygonGeometry | MultiPolygonGeometry;

export interface AdminProperties {
  id: string;
  name: string;
  level: "department" | "province";
  department_id: string;
}

export interface AdminFeature {
  type: "Feature";
  properties: AdminProperties;
  geometry: AdminGeometry;
}

export interface TerritoryIndex {
  departments: AdminRef[];
  provinces: AdminRef[];
  problem: string | null;
}

interface LatLon {
  lat: number;
  lon: number;
}

const REPLACE_HINT =
  "Sustituye front/data/bolivia-admin.json por un FeatureCollection con properties id, name, level (department o province) y department_id.";

const collection = rawCollection as unknown as {
  features?: Array<{
    type?: string;
    properties?: Partial<AdminProperties>;
    geometry?: AdminGeometry;
  }>;
};

const features: AdminFeature[] = [];
let problem: string | null = null;

for (const feature of collection.features ?? []) {
  const props = feature.properties;
  const geometry = feature.geometry;
  if (!props?.id || !props.name || !props.department_id) continue;
  if (props.level !== "department" && props.level !== "province") continue;
  if (!geometry || (geometry.type !== "Polygon" && geometry.type !== "MultiPolygon")) continue;
  features.push({
    type: "Feature",
    properties: {
      id: props.id,
      name: props.name,
      level: props.level,
      department_id: props.department_id,
    },
    geometry,
  });
}

const departments = features.filter((feature) => feature.properties.level === "department");
const provinces = features.filter((feature) => feature.properties.level === "province");
const byId = new Map(features.map((feature) => [feature.properties.id, feature]));

if (departments.length < 9 || provinces.length < 9) {
  problem = `Los límites locales están incompletos. ${REPLACE_HINT}`;
}

const refCache = new Map<string, AdminRef>();

export function territoryIndex(): TerritoryIndex {
  return {
    departments: departments.map(toRef).sort(byName),
    provinces: provinces.map(toRef).sort(byName),
    problem,
  };
}

export function findAdmin(id: string | null | undefined): AdminFeature | null {
  if (!id) return null;
  return byId.get(id) ?? null;
}

export function provincesOf(departmentId: string | null): AdminFeature[] {
  if (!departmentId) return [];
  return provinces
    .filter((feature) => feature.properties.department_id === departmentId)
    .sort((a, b) => a.properties.name.localeCompare(b.properties.name, "es"));
}

export function sampleInside(feature: AdminFeature, count: number): LatLon[] {
  const bounds = boundsOf(feature.geometry);
  const found: LatLon[] = [];
  const steps = 9;
  for (let y = 0; y < steps; y += 1) {
    for (let x = 0; x < steps; x += 1) {
      const lon = bounds.west + ((x + 0.5) / steps) * widthOf(bounds);
      const lat = bounds.south + ((y + 0.5) / steps) * heightOf(bounds);
      if (contains(feature.geometry, lon, lat)) found.push({ lat, lon });
    }
  }
  if (found.length === 0) {
    found.push({
      lat: (bounds.south + bounds.north) / 2,
      lon: (bounds.west + bounds.east) / 2,
    });
  }
  const origin = meanPoint(found);
  const pool = [...found];
  const chosen: LatLon[] = [];
  const firstIndex = pool.reduce(
    (best, point, index) => (distance(point, origin) < distance(pool[best], origin) ? index : best),
    0,
  );
  chosen.push(pool.splice(firstIndex, 1)[0]);
  while (chosen.length < count && pool.length > 0) {
    let pick = 0;
    let farthest = -1;
    pool.forEach((point, index) => {
      const gap = nearest(point, chosen);
      if (gap > farthest) {
        farthest = gap;
        pick = index;
      }
    });
    chosen.push(pool.splice(pick, 1)[0]);
  }
  while (chosen.length < count) {
    const last = chosen[chosen.length - 1];
    chosen.push({ lat: last.lat + 0.04, lon: last.lon + 0.04 });
  }
  return chosen.slice(0, count);
}

function toRef(feature: AdminFeature): AdminRef {
  const cached = refCache.get(feature.properties.id);
  if (cached) return cached;
  const point = representative(feature);
  const ref: AdminRef = {
    id: feature.properties.id,
    name: feature.properties.name,
    level: feature.properties.level,
    department_id: feature.properties.department_id,
    lat: round(point.lat),
    lon: round(point.lon),
  };
  refCache.set(feature.properties.id, ref);
  return ref;
}

function representative(feature: AdminFeature): LatLon {
  const [point] = sampleInside(feature, 1);
  return point;
}

function byName(a: AdminRef, b: AdminRef): number {
  return a.name.localeCompare(b.name, "es");
}

function boundsOf(geometry: AdminGeometry): { west: number; east: number; south: number; north: number } {
  let west = Infinity;
  let east = -Infinity;
  let south = Infinity;
  let north = -Infinity;
  eachRing(geometry, (ring) => {
    for (const [lon, lat] of ring) {
      west = Math.min(west, lon);
      east = Math.max(east, lon);
      south = Math.min(south, lat);
      north = Math.max(north, lat);
    }
  });
  return { west, east, south, north };
}

function widthOf(bounds: { west: number; east: number }): number {
  return Math.max(bounds.east - bounds.west, 0.01);
}

function heightOf(bounds: { south: number; north: number }): number {
  return Math.max(bounds.north - bounds.south, 0.01);
}

function eachRing(geometry: AdminGeometry, visit: (ring: LinearRing) => void): void {
  if (geometry.type === "Polygon") {
    geometry.coordinates.forEach(visit);
    return;
  }
  geometry.coordinates.forEach((polygon) => polygon.forEach(visit));
}

function contains(geometry: AdminGeometry, lon: number, lat: number): boolean {
  if (geometry.type === "Polygon") return polygonContains(geometry.coordinates, lon, lat);
  return geometry.coordinates.some((polygon) => polygonContains(polygon, lon, lat));
}

function polygonContains(rings: LinearRing[], lon: number, lat: number): boolean {
  if (!ringContains(rings[0], lon, lat)) return false;
  for (let hole = 1; hole < rings.length; hole += 1) {
    if (ringContains(rings[hole], lon, lat)) return false;
  }
  return true;
}

function ringContains(ring: LinearRing, lon: number, lat: number): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i, i += 1) {
    const xi = ring[i][0];
    const yi = ring[i][1];
    const xj = ring[j][0];
    const yj = ring[j][1];
    const crosses = yi > lat !== yj > lat;
    if (crosses && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

function meanPoint(points: LatLon[]): LatLon {
  const total = points.reduce(
    (sum, point) => ({ lat: sum.lat + point.lat, lon: sum.lon + point.lon }),
    { lat: 0, lon: 0 },
  );
  return { lat: total.lat / points.length, lon: total.lon / points.length };
}

function distance(a: LatLon, b: LatLon): number {
  return (a.lat - b.lat) ** 2 + (a.lon - b.lon) ** 2;
}

function nearest(point: LatLon, others: LatLon[]): number {
  return Math.min(...others.map((other) => distance(point, other)));
}

function round(value: number): number {
  return Math.round(value * 10000) / 10000;
}
