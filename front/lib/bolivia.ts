import rawCollection from "@/data/bolivia-admin.json";
import type { BBox } from "@/lib/types";

type Ring = [number, number][];

type DepartmentGeometry =
  | { type: "Polygon"; coordinates: Ring[] }
  | { type: "MultiPolygon"; coordinates: Ring[][] };

export interface DepartmentFeature {
  type: "Feature";
  properties: { id: string; name: string; department_id?: string };
  geometry: DepartmentGeometry;
}

interface RawFeature {
  properties?: { id?: string; name?: string; level?: string; department_id?: string };
  geometry?: { type?: string };
}

const raw = (rawCollection as unknown as { features?: RawFeature[] }).features ?? [];

/** Límites de los 9 departamentos (GeoBolivia), solo como contexto en el mapa. */
export const departments: { type: "FeatureCollection"; features: DepartmentFeature[] } = {
  type: "FeatureCollection",
  features: raw
    .filter(
      (feature) =>
        feature.properties?.level === "department" &&
        feature.properties.id &&
        feature.properties.name &&
        (feature.geometry?.type === "Polygon" || feature.geometry?.type === "MultiPolygon"),
    )
    .map((feature) => ({
      type: "Feature" as const,
      properties: { id: String(feature.properties?.id), name: String(feature.properties?.name) },
      geometry: feature.geometry as DepartmentGeometry,
    })),
};

/** Provincias (GeoBolivia). En el mapa de focos se dibujan para reconocer el territorio. */
export const provinces: { type: "FeatureCollection"; features: DepartmentFeature[] } = {
  type: "FeatureCollection",
  features: raw
    .filter(
      (feature) =>
        feature.properties?.level === "province" &&
        feature.properties.id &&
        feature.properties.name &&
        (feature.geometry?.type === "Polygon" || feature.geometry?.type === "MultiPolygon"),
    )
    .map((feature) => ({
      type: "Feature" as const,
      properties: {
        id: String(feature.properties?.id),
        name: String(feature.properties?.name),
        department_id: feature.properties?.department_id,
      },
      geometry: feature.geometry as DepartmentGeometry,
    })),
};

const byName = (a: DepartmentFeature, b: DepartmentFeature) =>
  a.properties.name.localeCompare(b.properties.name, "es");

const boundsCache = new WeakMap<DepartmentFeature, BBox>();

/** Provincias del departamento elegido. El id de la región es el del departamento. */
export function provincesForRegion(regionId: string): DepartmentFeature[] {
  return provinces.features.filter((feature) => feature.properties.department_id === regionId).sort(byName);
}

export function featureBounds(feature: DepartmentFeature): BBox {
  const cached = boundsCache.get(feature);
  if (cached) return cached;
  const bounds = { west: Infinity, east: -Infinity, south: Infinity, north: -Infinity };
  const visit = (pair: unknown) => {
    if (!Array.isArray(pair)) return;
    if (typeof pair[0] === "number" && typeof pair[1] === "number") {
      bounds.west = Math.min(bounds.west, pair[0]);
      bounds.east = Math.max(bounds.east, pair[0]);
      bounds.south = Math.min(bounds.south, pair[1]);
      bounds.north = Math.max(bounds.north, pair[1]);
      return;
    }
    pair.forEach(visit);
  };
  visit(feature.geometry.coordinates);
  boundsCache.set(feature, bounds);
  return bounds;
}

/** True si el rectángulo de la celda toca el polígono, aunque el centro quede afuera. */
export function featureHitsCell(
  feature: DepartmentFeature,
  lat: number,
  lon: number,
  dlat: number,
  dlon: number,
): boolean {
  const south = lat - dlat / 2;
  const north = lat + dlat / 2;
  const west = lon - dlon / 2;
  const east = lon + dlon / 2;
  const bounds = featureBounds(feature);
  if (east < bounds.west || west > bounds.east || north < bounds.south || south > bounds.north) return false;
  const samples: Array<[number, number]> = [
    [lon, lat],
    [west, south],
    [west, north],
    [east, south],
    [east, north],
    [lon, south],
    [lon, north],
    [west, lat],
    [east, lat],
  ];
  if (samples.some(([x, y]) => featureCovers(feature, x, y))) return true;
  const geometry = feature.geometry;
  const rings = geometry.type === "Polygon" ? geometry.coordinates : geometry.coordinates.flat();
  return rings.some((ring) => ringHitsRect(ring, west, south, east, north));
}

function ringHitsRect(ring: Ring, west: number, south: number, east: number, north: number): boolean {
  for (const [x, y] of ring) {
    if (x >= west && x <= east && y >= south && y <= north) return true;
  }
  const edges: Array<[number, number, number, number]> = [
    [west, south, east, south],
    [east, south, east, north],
    [east, north, west, north],
    [west, north, west, south],
  ];
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i, i += 1) {
    const [x1, y1] = ring[j];
    const [x2, y2] = ring[i];
    for (const [ax, ay, bx, by] of edges) {
      if (segmentsCross(x1, y1, x2, y2, ax, ay, bx, by)) return true;
    }
  }
  return false;
}

function segmentsCross(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  x3: number,
  y3: number,
  x4: number,
  y4: number,
): boolean {
  const denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4);
  if (denom === 0) return false;
  const t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom;
  const u = ((x1 - x3) * (y1 - y2) - (y1 - y3) * (x1 - x2)) / denom;
  return t >= 0 && t <= 1 && u >= 0 && u <= 1;
}

/** True si el punto (lon, lat) cae dentro del polígono, agujeros incluidos. */
export function featureCovers(feature: DepartmentFeature, lon: number, lat: number): boolean {
  const bounds = featureBounds(feature);
  if (lon < bounds.west || lon > bounds.east || lat < bounds.south || lat > bounds.north) return false;
  const geometry = feature.geometry;
  if (geometry.type === "Polygon") return polygonCovers(geometry.coordinates, lon, lat);
  return geometry.coordinates.some((polygon) => polygonCovers(polygon, lon, lat));
}

function polygonCovers(rings: Ring[], lon: number, lat: number): boolean {
  if (!ringCovers(rings[0], lon, lat)) return false;
  for (let hole = 1; hole < rings.length; hole += 1) {
    if (ringCovers(rings[hole], lon, lat)) return false;
  }
  return true;
}

function ringCovers(ring: Ring, lon: number, lat: number): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i, i += 1) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    const crosses = yi > lat !== yj > lat;
    if (crosses && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}
