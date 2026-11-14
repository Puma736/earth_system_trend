export interface TrendResult {
  slopePerStep: number;
  z: number;
  p: number;
  n: number;
}

export function mannKendall(values: number[]): TrendResult {
  const n = values.length;
  if (n < 8) {
    return { slopePerStep: 0, z: 0, p: 1, n };
  }

  let s = 0;
  const slopes: number[] = [];
  for (let i = 0; i < n - 1; i += 1) {
    for (let j = i + 1; j < n; j += 1) {
      const diff = values[j] - values[i];
      if (diff > 0) s += 1;
      else if (diff < 0) s -= 1;
      slopes.push(diff / (j - i));
    }
  }

  const variance = (n * (n - 1) * (2 * n + 5)) / 18;
  const zStat =
    s > 0 ? (s - 1) / Math.sqrt(variance) : s < 0 ? (s + 1) / Math.sqrt(variance) : 0;
  const p = 2 * (1 - normalCdf(Math.abs(zStat)));
  slopes.sort((a, b) => a - b);
  const mid = Math.floor(slopes.length / 2);
  const slopePerStep =
    slopes.length % 2 === 0 ? (slopes[mid - 1] + slopes[mid]) / 2 : slopes[mid];

  return { slopePerStep, z: zStat, p: clamp01(p), n };
}

export function bestLag(
  driver: number[],
  response: number[],
  maxLag: number,
): { lag: number; r: number; p: number; n: number } | null {
  let best: { lag: number; r: number; p: number; n: number } | null = null;
  for (let lag = 0; lag <= maxLag; lag += 1) {
    const a = driver.slice(0, driver.length - lag);
    const b = response.slice(lag);
    const n = Math.min(a.length, b.length);
    if (n < 8) continue;
    const r = pearson(a.slice(0, n), b.slice(0, n));
    if (!Number.isFinite(r)) continue;
    const p = correlationP(r, n);
    if (!best || Math.abs(r) > Math.abs(best.r)) {
      best = { lag, r, p, n };
    }
  }
  return best;
}

export function pearson(a: number[], b: number[]): number {
  const n = Math.min(a.length, b.length);
  if (n < 3) return Number.NaN;
  let sa = 0;
  let sb = 0;
  for (let i = 0; i < n; i += 1) {
    sa += a[i];
    sb += b[i];
  }
  const ma = sa / n;
  const mb = sb / n;
  let num = 0;
  let da = 0;
  let db = 0;
  for (let i = 0; i < n; i += 1) {
    const xa = a[i] - ma;
    const xb = b[i] - mb;
    num += xa * xb;
    da += xa * xa;
    db += xb * xb;
  }
  if (da === 0 || db === 0) return 0;
  return num / Math.sqrt(da * db);
}

function correlationP(r: number, n: number): number {
  const clipped = Math.max(-0.999999, Math.min(0.999999, r));
  if (n <= 3) return 1;
  const z = Math.atanh(clipped) * Math.sqrt(n - 3);
  return clamp01(2 * (1 - normalCdf(Math.abs(z))));
}

function normalCdf(x: number): number {
  const t = 1 / (1 + 0.2316419 * Math.abs(x));
  const d = 0.3989422804014327 * Math.exp((-x * x) / 2);
  const p =
    d *
    t *
    (0.319381530 +
      t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
  return x >= 0 ? 1 - p : p;
}

function clamp01(value: number): number {
  if (value < 0) return 0;
  if (value > 1) return 1;
  return value;
}
