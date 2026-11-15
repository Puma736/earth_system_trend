import { formatCount } from "./format";

/**
 * Escala de calor del mapa de focos. Más detecciones, rojo más oscuro.
 * `ink` es el color del número dentro del cuadro. Los cortes no cambian,
 * así dos años se comparan con la misma escala.
 */
export const HOTSPOT_BINS = [
  { min: 1, max: 24, color: "#f3c4b4", ink: "#151722" },
  { min: 25, max: 99, color: "#e8876c", ink: "#151722" },
  { min: 100, max: 249, color: "#d14b38", ink: "#151722" },
  { min: 250, max: 999, color: "#a3201c", ink: "#f6f8d4" },
  { min: 1000, max: Number.POSITIVE_INFINITY, color: "#6e1210", ink: "#f6f8d4" },
] as const;

export type HotspotBin = (typeof HOTSPOT_BINS)[number];

export function binFor(count: number): HotspotBin {
  return HOTSPOT_BINS.find((bin) => count <= bin.max) ?? HOTSPOT_BINS[HOTSPOT_BINS.length - 1];
}

export function binLabel(bin: HotspotBin): string {
  return Number.isFinite(bin.max) ? `${formatCount(bin.min)}–${formatCount(bin.max)}` : `${formatCount(bin.min)}+`;
}
