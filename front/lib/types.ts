/**
 * Contrato de la API. Es el espejo de backend/app/schemas.py y de docs/api.md:
 * si cambia allí, cambia aquí.
 */

export type Verdict = "Real change" | "Not yet certain" | "Not enough data";

export interface BBox {
  west: number;
  south: number;
  east: number;
  north: number;
}

export interface Region {
  id: string;
  name: string;
  bbox: BBox;
  note: string;
}

export interface Season {
  id: string;
  name: string;
  months: number[];
}

export interface YearRange {
  start: number;
  end: number;
}

export interface IndicatorInfo {
  param: string;
  label: string;
  unit: string;
  definition: string;
}

/** GET /api/regions */
export interface Catalog {
  regions: Region[];
  seasons: Season[];
  years: { drought: YearRange; hotspots: YearRange };
  indicators: IndicatorInfo[];
}

export interface YearValue {
  year: number;
  value: number;
}

export interface Trend {
  slope_per_decade: number;
  /** Valor de la recta de Sen en el primer año de la serie. */
  intercept: number;
  p_value: number;
  /** p corregido por FDR entre los 6 indicadores. Solo en la sequía. */
  q_value: number | null;
  n_years: number;
  method: string;
  slope_low_per_decade: number;
  slope_high_per_decade: number;
  total_change: number;
  ols_slope_per_decade: number;
  ols_p_value: number;
  notes: string[];
}

export interface DroughtIndicator extends IndicatorInfo {
  series: YearValue[];
  trend: Trend | null;
  points_to_drying: boolean | null;
  verdict: Verdict;
}

/** GET /api/drought */
export interface DroughtResponse {
  region: Region;
  season: Season;
  start: number;
  end: number;
  source: string;
  summary: {
    pointing_to_drying: number;
    real_changes: number;
    total: number;
    text: string;
  };
  indicators: DroughtIndicator[];
}

/** GET /api/hotspots */
export interface HotspotsResponse {
  region: Region;
  season: Season;
  start: number;
  end: number;
  source: string;
  series: YearValue[];
  trend: Trend | null;
  percent_change: number | null;
  verdict: Verdict;
}

export interface HotspotCell {
  lat: number;
  lon: number;
  count: number;
}

/** GET /api/hotspots/grid */
export interface HotspotGridResponse {
  region: Region;
  season: Season;
  year: number;
  cell_deg: number;
  cells: HotspotCell[];
}

export interface LinkPoint {
  year: number;
  drought_value: number;
  hotspots: number;
}

/** GET /api/link */
export interface LinkResponse {
  region: Region;
  season: Season;
  indicator: string;
  indicator_label: string;
  indicator_unit: string;
  points: LinkPoint[];
  rho: number | null;
  p_value: number | null;
  n_years: number;
  method: string;
  caveat: string;
}
