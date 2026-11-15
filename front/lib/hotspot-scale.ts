import { formatCount } from "./format";

/**
 * Escala del mapa de focos por celda de 0,5°. Son pasos de la rampa "signal"
 * de theme.ts, de oscuro (pocos focos) a claro (muchos), validados sobre el
 * fondo #151722: un solo tono, luminosidad creciente y contraste >= 2:1.
 * Los cortes son fijos para que dos años se puedan comparar a simple vista.
 */
export const HOTSPOT_BINS = [
  { min: 1, max: 24, color: "#6a7318" },
  { min: 25, max: 99, color: "#8e9920" },
  { min: 100, max: 249, color: "#b3c028" },
  { min: 250, max: 999, color: "#d5db45" },
  { min: 1000, max: Number.POSITIVE_INFINITY, color: "#f6f8d4" },
] as const;

export type HotspotBin = (typeof HOTSPOT_BINS)[number];

export function binFor(count: number): HotspotBin {
  return HOTSPOT_BINS.find((bin) => count <= bin.max) ?? HOTSPOT_BINS[HOTSPOT_BINS.length - 1];
}

export function binLabel(bin: HotspotBin): string {
  return Number.isFinite(bin.max) ? `${formatCount(bin.min)}–${formatCount(bin.max)}` : `${formatCount(bin.min)}+`;
}
