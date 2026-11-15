import rawCollection from "@/data/bolivia-admin.json";

type Ring = [number, number][];

type DepartmentGeometry =
  | { type: "Polygon"; coordinates: Ring[] }
  | { type: "MultiPolygon"; coordinates: Ring[][] };

export interface DepartmentFeature {
  type: "Feature";
  properties: { id: string; name: string };
  geometry: DepartmentGeometry;
}

interface RawFeature {
  properties?: { id?: string; name?: string; level?: string };
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
