export type VariableId =
  | "precipitation"
  | "temperature"
  | "ndvi"
  | "soil_moisture"
  | "lst";

export type CaseId = "drought" | "heat" | "signal";

export type Aggregation = "monthly" | "annual";

export interface Region {
  id: string;
  name: string;
  lat: number;
  lon: number;
}

export interface VariableDef {
  id: VariableId;
  code: string;
  name: string;
  unit: string;
  definition: string;
  source: string;
}

export interface Question {
  id: string;
  text: string;
}

export interface CaseDef {
  id: CaseId;
  label: string;
  variables: VariableId[];
  questions: Question[];
}

export interface PlaceRef {
  name: string;
  lat: number;
  lon: number;
}

export interface AdminRef {
  id: string;
  name: string;
  level: "department" | "province";
  department_id: string;
  lat: number;
  lon: number;
}

export type MapFocus =
  | { kind: "bolivia" }
  | { kind: "department"; id: string }
  | { kind: "province"; id: string }
  | { kind: "place"; name: string; lat: number; lon: number };

export interface Catalog {
  regions: Region[];
  variables: VariableDef[];
  cases: CaseDef[];
  departments?: AdminRef[];
  provinces?: AdminRef[];
}

export interface InvestigationQuery {
  region_id: string;
  case_id: CaseId;
  question_id: string;
  variables: VariableId[];
  start: string;
  end: string;
  aggregation: Aggregation;
  department_id: string | null;
  province_id: string | null;
  place: PlaceRef | null;
}

export interface SeriesPoint {
  date: string;
  value: number;
  anomaly: number;
  z: number;
}

export interface Series {
  variable: VariableId;
  unit: string;
  points: SeriesPoint[];
  /** Prolongación de la pendiente de Sen. Solo viene en la pregunta de proyección. */
  forecast?: SeriesPoint[];
}

export interface MapCell {
  id: string;
  name: string;
  lat: number;
  lon: number;
  value: number;
  selected: boolean;
}

export interface TrendStat {
  variable: VariableId;
  test: "mann_kendall";
  /** Pendiente de Sen por década, para lectura larga. */
  slope_per_decade: number;
  /** Pendiente de Sen por periodo, como la publica el laboratorio. */
  slope_per_step: number;
  p_value: number;
  significant: boolean;
  n: number;
  direction: "up" | "down" | "flat";
  r_squared: number;
  n_anomalies: number;
  last_z: number;
  change_date: string | null;
  mean: number;
  projected_mean: number;
  projected_pct: number;
}

export interface PatternSummary {
  pc1_share: number | null;
  period_steps: number | null;
  period_unit: "months" | "years";
  variable: VariableId;
}

export interface LagRelation {
  driver: VariableId;
  response: VariableId;
  lag: number;
  lag_unit: "months" | "years";
  r: number;
  p_value: number;
  n: number;
  sentence: string;
}

export interface Hotspot {
  lat: number;
  lon: number;
  date: string;
}

export interface EventWindow {
  kind: "drought" | "thermal_stress";
  start: string;
  end: string;
  duration: number;
  duration_unit: "months" | "years";
  intensity: number;
  intensity_unit: string;
  extent_count: number;
  extent_total: number;
  recovery_note: string | null;
}

export interface InvestigationResult {
  query: InvestigationQuery;
  series: Series[];
  map_cells: MapCell[];
  map_variable: VariableId;
  map_caption: string;
  statistics: TrendStat[];
  relations: LagRelation[];
  sequence_label: string;
  event: EventWindow | null;
  hotspots: Hotspot[];
  pattern: PatternSummary;
  conclusion: string;
  caveat: string;
  source: "demo" | "api";
}
