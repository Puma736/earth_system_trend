import type { Season } from "./types";

const MINUS = "−";
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const SIG2 = new Intl.NumberFormat("en-US", { maximumSignificantDigits: 2 });
const SIG3 = new Intl.NumberFormat("en-US", { maximumSignificantDigits: 3 });
const COUNT = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const COMPACT = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });

function typographicMinus(text: string): string {
  return text.replace("-", MINUS);
}

/** Valor de una serie, con 3 cifras significativas. */
export function formatNumber(value: number): string {
  if (!Number.isFinite(value)) return "n/a";
  return typographicMinus(SIG3.format(value));
}

/** Cambio con signo explícito: +0.57, −0.021. */
export function formatSigned(value: number, digits: 2 | 3 = 2): string {
  if (!Number.isFinite(value)) return "n/a";
  const text = (digits === 2 ? SIG2 : SIG3).format(Math.abs(value));
  if (Number(text.replace(/,/g, "")) === 0) return "0";
  return `${value < 0 ? MINUS : "+"}${text}`;
}

export function formatCount(value: number): string {
  return typographicMinus(COUNT.format(Math.round(value)));
}

/** Marcas del eje: 0, 50K, 100K. */
export function formatCompact(value: number): string {
  return typographicMinus(COMPACT.format(value));
}

export function formatP(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "n/a";
  if (value < 0.001) return "< 0.001";
  return SIG2.format(value);
}

/** "p < 0.001" o "q = 0.21": el signo de comparación va una sola vez. */
export function pClause(symbol: "p" | "q", value: number | null | undefined): string {
  const text = formatP(value);
  return text.startsWith("<") ? `${symbol} ${text}` : `${symbol} = ${text}`;
}

/** Número con decimales fijos y menos tipográfico: ρ = −0.71. */
export function formatFixed(value: number, decimals: number): string {
  if (!Number.isFinite(value)) return "n/a";
  return typographicMinus(value.toFixed(decimals));
}

export function formatPercent(value: number): string {
  return `${formatSigned(value)}%`;
}

/** "−0.14 mm/day", "−1.8%", "−0.021" (las fracciones 0-1 no llevan unidad). */
export function withUnit(text: string, unit: string): string {
  if (unit === "0-1" || unit === "") return text;
  if (unit === "%") return `${text}%`;
  return `${text} ${unit}`;
}

export function unitLabel(unit: string): string {
  return unit === "0-1" ? "0 to 1" : unit;
}

/** Meses de una época: "Jun–Oct", "Aug–Sep" o "full year". */
export function monthRange(months: number[]): string {
  if (months.length === 12) return "full year";
  const sorted = [...months].sort((a, b) => a - b);
  const contiguous = sorted.every((month, index) => index === 0 || month === sorted[index - 1] + 1);
  const names = sorted.map((month) => MONTHS[month - 1] ?? String(month));
  if (!contiguous) return names.join(", ");
  return names.length === 1 ? names[0] : `${names[0]}–${names[names.length - 1]}`;
}

/** Nombre corto para los botones: el nombre de la época sin el paréntesis final. */
export function seasonShort(season: Season): string {
  return season.name.replace(/\s*\([^)]*\)\s*$/, "") || season.name;
}

export function formatLat(lat: number): string {
  return `${Math.abs(lat).toFixed(2)}°${lat < 0 ? "S" : "N"}`;
}

export function formatLon(lon: number): string {
  return `${Math.abs(lon).toFixed(2)}°${lon < 0 ? "W" : "E"}`;
}

/** "−2.9σ": anomalía en desviaciones estándar del período normal. */
export function formatSigma(z: number | null): string {
  if (z === null || !Number.isFinite(z)) return "n/a";
  return `${formatFixed(z, 1).replace(/^(\d)/, "+$1")}σ`;
}

function ordinal(n: number): string {
  const tens = n % 100;
  if (tens >= 11 && tens <= 13) return `${n}th`;
  return `${n}${({ 1: "st", 2: "nd", 3: "rd" } as Record<number, string>)[n % 10] ?? "th"}`;
}

/** "lowest of 45 years", "3rd highest of 23 years". */
export function rankPhrase(rank: number, of: number, by: "lowest" | "highest"): string {
  return `${rank === 1 ? "" : `${ordinal(rank)} `}${by} of ${of} years`;
}
