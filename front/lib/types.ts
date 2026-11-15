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
  /** Primer año de un nuevo nivel (prueba de Pettitt). Mostrarlo solo si change_p_value < 0.05. */
  change_year: number | null;
  change_p_value: number | null;
  change_mean_before: number | null;
  change_mean_after: number | null;
}

export interface Baseline {
  start: number;
  end: number;
  mean: number;
  /** Desviación estándar muestral de los años del período base. */
  sd: number;
}

/** Anomalía de un año frente al período normal (backend/app/stats/anomaly.py). */
export interface YearAnomaly {
  year: number;
  /** Valor menos la media del período base, en la unidad del indicador. */
  anomaly: number;
  /** Anomalía en desviaciones estándar del período base. null si la base es plana. */
  z: number | null;
  /** Valor como % de la media del período base. null si la media no es positiva. */
  percent_of_normal: number | null;
  /** 1 = el año más extremo de todo el registro. */
  rank: number;
}

/** Campos de anomalías que comparten /api/drought (por indicador) y /api/hotspots. */
export interface AnomalyFields {
  baseline: Baseline | null;
  anomalies: YearAnomaly[];
  /** Años del registro completo con los que se calcula el puesto. */
  rank_of: number;
  /** El puesto 1 es el valor más bajo o el más alto. */
  rank_by: "lowest" | "highest";
}

export interface DroughtIndicator extends IndicatorInfo, AnomalyFields {
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
export interface HotspotsResponse extends AnomalyFields {
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

/** GET /api/hotspots/places */
export interface PlaceGridResponse {
  place_id: string;
  name: string;
  season: Season;
  year: number;
  cell_deg: number;
  cells: HotspotCell[];
  note: string;
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

export interface LeadItem {
  param: string;
  label: string;
  unit: string;
  rho: number | null;
  p_value: number | null;
  /** p corregido por FDR entre los 6 indicadores. */
  q_value: number | null;
  n_years: number;
  verdict: Verdict;
}

/** GET /api/lead: la época húmeda anterior (oct-mar) frente a los focos de la época elegida. */
export interface LeadResponse {
  region: Region;
  season: Season;
  start: number;
  end: number;
  wet_months: number[];
  items: LeadItem[];
  method: string;
  caveat: string;
}
