import { findAdmin, sampleInside } from "./bolivia";
import { CAVEAT, demoCatalog } from "./catalog";
import { bestLag, mannKendall } from "./stats";
import type {
  Aggregation,
  EventWindow,
  Hotspot,
  InvestigationQuery,
  InvestigationResult,
  LagRelation,
  MapCell,
  Series,
  SeriesPoint,
  TrendStat,
  VariableId,
} from "./types";

const Z_SCALE: Record<VariableId, number> = {
  precipitation: 20,
  temperature: 0.6,
  ndvi: 0.05,
  soil_moisture: 0.05,
  wind: 0.3,
};

const REGION_DRYNESS: Record<string, number> = {
  bolivia: 1,
  chaco: 1.3,
  santa_cruz: 1.15,
  beni: 0.9,
  cochabamba: 0.7,
  la_paz: 0.55,
};

const PLACES: { id: string; name: string; lat: number; lon: number; dryness: number }[] = [
  { id: "la_paz", name: "La Paz", lat: -16.5, lon: -68.15, dryness: 0.55 },
  { id: "cochabamba", name: "Cochabamba", lat: -17.39, lon: -66.16, dryness: 0.7 },
  { id: "santa_cruz", name: "Santa Cruz", lat: -17.78, lon: -63.18, dryness: 1.15 },
  { id: "beni", name: "Beni", lat: -14.83, lon: -64.9, dryness: 0.9 },
  { id: "chaco", name: "Chaco", lat: -20.04, lon: -63.52, dryness: 1.3 },
  { id: "pando", name: "Pando", lat: -11.03, lon: -68.77, dryness: 0.4 },
];

export function buildDemoResult(query: InvestigationQuery): InvestigationResult {
  const monthly = buildMonthly(query);
  const series = query.aggregation === "annual" ? toAnnual(monthly) : monthly;
  const names = Object.fromEntries(demoCatalog.variables.map((item) => [item.id, item.name]));
  const units = Object.fromEntries(demoCatalog.variables.map((item) => [item.id, item.unit]));
  const statistics = series.map((item) => trendFor(item, query.aggregation));
  const relations = relate(series, names, query.aggregation);
  const mapVariable = focusVariable(query);
  const event = detectEvent(query, series, mapVariable, units[mapVariable] ?? "");
  const mapCells = mapFor(query, series, mapVariable, event);
  const hotspots = query.case_id === "fire" ? demoHotspots(event, query) : [];
  const sequence = sequenceLabel(relations, names);

  return {
    query,
    series,
    map_cells: mapCells,
    map_variable: mapVariable,
    map_caption: mapCaption(query, names[mapVariable] ?? mapVariable, event),
    statistics,
    relations,
    sequence_label: sequence,
    event,
    hotspots,
    conclusion: writeConclusion(query, statistics, relations, event, hotspots, names, units),
    caveat: CAVEAT,
    source: "demo",
  };
}

function buildMonthly(query: InvestigationQuery): Series[] {
  const start = parseMonth(query.start);
  const end = parseMonth(query.end);
  const count = monthIndex(end.year, end.month) - monthIndex(start.year, start.month) + 1;
  const dryness = REGION_DRYNESS[query.region_id] ?? 1;
  const rand = mulberry32(hashString(`${query.region_id}:${query.start}:${query.end}`));
  const droughtAt = Math.round(count * 0.62);
  const fireAt = Math.round(count * 0.78);

  return query.variables.map((variable) => {
    const points: SeriesPoint[] = [];
    for (let i = 0; i < count; i += 1) {
      const cursor = addMonths(start.year, start.month, i);
      const month = cursor.month;
      const base = climatology(variable, month);
      const t = count <= 1 ? 0 : i / (count - 1);
      let anomaly = (rand() - 0.5) * noise(variable);
      anomaly += trendDrift(variable) * t;
      anomaly += eventPulse(variable, i, droughtAt, 3) * dryness;
      anomaly += firePulse(variable, i, fireAt, 4) * dryness;
      const value = Math.max(0, base + anomaly);
      points.push({
        date: `${cursor.year}-${String(month).padStart(2, "0")}`,
        value: round(value, variable),
        anomaly: round(anomaly, variable),
        z: anomaly / Z_SCALE[variable],
      });
    }
    const unit = demoCatalog.variables.find((item) => item.id === variable)?.unit ?? "";
    return { variable, unit, points };
  });
}

function toAnnual(series: Series[]): Series[] {
  return series.map((item) => {
    const buckets = new Map<string, SeriesPoint[]>();
    for (const point of item.points) {
      const year = point.date.slice(0, 4);
      const group = buckets.get(year) ?? [];
      group.push(point);
      buckets.set(year, group);
    }
    const points = [...buckets.entries()].map(([year, group]) => ({
      date: year,
      value: round(mean(group.map((point) => point.value)), item.variable),
      anomaly: round(mean(group.map((point) => point.anomaly)), item.variable),
      z: mean(group.map((point) => point.z)),
    }));
    return { ...item, points };
  });
}

function trendFor(series: Series, aggregation: Aggregation): TrendStat {
  const fitted = mannKendall(series.points.map((point) => point.anomaly));
  const perDecade = aggregation === "annual" ? fitted.slopePerStep * 10 : fitted.slopePerStep * 120;
  const direction = perDecade > 0.0001 ? "up" : perDecade < -0.0001 ? "down" : "flat";
  return {
    variable: series.variable,
    test: "mann_kendall",
    slope_per_decade: perDecade,
    p_value: fitted.p,
    significant: fitted.n >= 8 && fitted.p < 0.05,
    n: fitted.n,
    direction,
  };
}

function relate(
  series: Series[],
  names: Record<string, string>,
  aggregation: Aggregation,
): LagRelation[] {
  const found: LagRelation[] = [];
  for (let i = 0; i < series.length; i += 1) {
    for (let j = 0; j < series.length; j += 1) {
      if (i === j) continue;
      const lag = bestLag(
        series[i].points.map((point) => point.z),
        series[j].points.map((point) => point.z),
        3,
      );
      if (!lag || Math.abs(lag.r) < 0.3 || lag.p >= 0.05) continue;
      found.push({
        driver: series[i].variable,
        response: series[j].variable,
        lag: lag.lag,
        lag_unit: aggregation === "annual" ? "years" : "months",
        r: lag.r,
        p_value: lag.p,
        n: lag.n,
        sentence: relationSentence(
          series[i].variable,
          series[j].variable,
          lag.lag,
          aggregation,
          lag.r,
          lag.p,
          lag.n,
          names,
        ),
      });
    }
  }

  const kept = new Map<string, LagRelation>();
  for (const relation of found) {
    const key = [relation.driver, relation.response].sort().join(":");
    const current = kept.get(key);
    kept.set(key, current ? preferPrecedence(current, relation) : relation);
  }
  return [...kept.values()]
    .sort((a, b) => {
      const lagged = Number(b.lag > 0) - Number(a.lag > 0);
      if (lagged !== 0) return lagged;
      return Math.abs(b.r) - Math.abs(a.r);
    })
    .slice(0, 4);
}

function relationSentence(
  driver: VariableId,
  response: VariableId,
  lag: number,
  aggregation: Aggregation,
  r: number,
  p: number,
  n: number,
  names: Record<string, string>,
): string {
  const sense = r >= 0 ? "en el mismo sentido" : "en sentido opuesto";
  const unit = aggregation === "annual" ? (lag === 1 ? "año" : "años") : lag === 1 ? "mes" : "meses";
  const same = aggregation === "annual" ? "en el mismo año" : "en el mismo mes";
  const when = lag === 0 ? same : `${lag} ${unit} después`;
  const pText = formatP(p);
  const pClause = pText.startsWith("<") ? `p ${pText}` : `p = ${pText}`;
  return `${names[driver]} y ${names[response]} se mueven ${sense} ${when} (r = ${r.toFixed(2)}, ${pClause}, n = ${n}).`;
}

function detectEvent(
  query: InvestigationQuery,
  series: Series[],
  mapVariable: VariableId,
  unit: string,
): EventWindow | null {
  const byId = new Map(series.map((item) => [item.variable, item]));
  if (query.case_id === "fire") return fireWindow(query, byId, unit);
  if (query.case_id === "drought") return droughtWindow(query, byId, mapVariable, unit);
  return null;
}

function droughtWindow(
  query: InvestigationQuery,
  byId: Map<VariableId, Series>,
  mapVariable: VariableId,
  unit: string,
): EventWindow | null {
  const precip = byId.get("precipitation");
  if (!precip) return null;
  const run = longestRun(precip.points, (point) => point.anomaly < -12);
  if (!run) return null;
  const intensity = Math.min(...run.points.map((point) => point.anomaly));
  const cells = spatialValues(query, "precipitation", run.start, run.end);
  return {
    kind: "drought",
    start: run.start,
    end: run.end,
    duration: run.points.length,
    duration_unit: query.aggregation === "annual" ? "years" : "months",
    intensity,
    intensity_unit: unit || precip.unit,
    extent_count: cells.filter((cell) => stressed("precipitation", cell.value)).length,
    extent_total: cells.length,
    recovery_note: recoveryNote(byId, run.end),
  };
}

function fireWindow(
  query: InvestigationQuery,
  byId: Map<VariableId, Series>,
  unit: string,
): EventWindow | null {
  const temperature = byId.get("temperature");
  const soil = byId.get("soil_moisture");
  const wind = byId.get("wind");
  const present = [temperature, soil, wind].filter(Boolean);
  if (present.length < 2 || !temperature) return null;
  const length = temperature.points.length;
  const flags = Array.from({ length }, (_, index) => {
    const warm = temperature.points[index].anomaly > 0.4;
    const dry = soil ? soil.points[index].anomaly < -0.04 : true;
    const windy = wind ? wind.points[index].anomaly > 0.15 : true;
    return warm && dry && windy;
  });
  const run = longestFlagRun(temperature.points, flags);
  if (!run) return null;
  const cells = spatialValues(query, "temperature", run.start, run.end);
  return {
    kind: "fire_favorable",
    start: run.start,
    end: run.end,
    duration: run.points.length,
    duration_unit: query.aggregation === "annual" ? "years" : "months",
    intensity: Math.max(...run.points.map((point) => point.anomaly)),
    intensity_unit: unit || temperature.unit,
    extent_count: cells.filter((cell) => stressed("temperature", cell.value)).length,
    extent_total: cells.length,
    recovery_note: null,
  };
}

function mapFor(
  query: InvestigationQuery,
  series: Series[],
  mapVariable: VariableId,
  event: EventWindow | null,
): MapCell[] {
  const focus = series.find((item) => item.variable === mapVariable);
  const end = focus?.points.at(-1)?.date ?? query.end;
  const cells = spatialValues(query, mapVariable, event?.start ?? end, event?.end ?? end);
  const provinceId = query.province_id;
  const placeSelected = Boolean(query.place) && !provinceId;
  return cells.map((cell) => ({
    ...cell,
    selected: provinceId
      ? cell.id === provinceId
      : placeSelected
        ? cell.id === "place"
        : cell.id === query.region_id,
  }));
}

function spatialValues(
  query: InvestigationQuery,
  variable: VariableId,
  start: string,
  end: string,
): MapCell[] {
  const national = buildMonthly({ ...query, region_id: "bolivia", variables: [variable] })[0];
  const slice = national.points.filter((point) => inWindow(point.date, start, end));
  const baseline = mean((slice.length > 0 ? slice : national.points).map((point) => point.anomaly));
  return anchorsFor(query).map((anchor) => ({
    id: anchor.id,
    name: anchor.name,
    lat: anchor.lat,
    lon: anchor.lon,
    value: baseline * anchor.factor,
    selected: false,
  }));
}

function anchorsFor(query: InvestigationQuery): Anchor[] {
  const province = query.province_id ? findAdmin(query.province_id) : null;
  if (province && province.properties.level === "province") {
    const points = sampleInside(province, 6);
    const compass = ["", "norte", "este", "sur", "oeste", "noreste"];
    const factors = [1.2, 0.7, 1.45, 0.85, 1.6, 0.55];
    return points.map((point, index) => ({
      id: index === 0 ? province.properties.id : `${province.properties.id}--${index}`,
      name: index === 0 ? province.properties.name : `${province.properties.name} ${compass[index] ?? index}`,
      lat: roundCoord(point.lat),
      lon: roundCoord(point.lon),
      factor: factors[index] ?? 1,
    }));
  }
  if (query.place) {
    const place = query.place;
    const offsets: Array<[number, number, string, number]> = [
      [0, 0, place.name, 1.2],
      [0.16, 0.08, `${place.name} norte`, 0.75],
      [-0.1, 0.14, `${place.name} este`, 1.4],
      [0.06, -0.16, `${place.name} sur`, 0.9],
      [-0.14, -0.08, `${place.name} oeste`, 1.15],
    ];
    return offsets.map(([dlat, dlon, name, factor], index) => ({
      id: index === 0 ? "place" : `place--${index}`,
      name,
      lat: roundCoord(place.lat + dlat),
      lon: roundCoord(place.lon + dlon),
      factor,
    }));
  }
  return PLACES.map((place) => ({
    id: place.id,
    name: place.name,
    lat: place.lat,
    lon: place.lon,
    factor: place.dryness,
  }));
}

function mapCaption(query: InvestigationQuery, name: string, event: EventWindow | null): string {
  const moment = event ? "durante el episodio" : "al final del intervalo";
  const province = query.province_id ? findAdmin(query.province_id) : null;
  const where = province
    ? ` en ${province.properties.name}`
    : query.place
      ? ` cerca de ${query.place.name}`
      : "";
  return `${name} ${moment}${where}. El tamaño es la magnitud de la anomalía.`;
}

function writeConclusion(
  query: InvestigationQuery,
  statistics: TrendStat[],
  relations: LagRelation[],
  event: EventWindow | null,
  hotspots: Hotspot[],
  names: Record<string, string>,
  units: Record<string, string>,
): string {
  const lead = leadSentence(query, statistics, relations, event, hotspots, names, units);
  const extra = relations
    .slice(0, 3)
    .map((relation) => relation.sentence)
    .filter((sentence) => !lead.includes(sentence));
  const scope = scopeSentence(query);
  return [scope, lead, ...extra].filter((part): part is string => Boolean(part)).join(" ");
}

function scopeSentence(query: InvestigationQuery): string | null {
  const province = query.province_id ? findAdmin(query.province_id) : null;
  const department = province
    ? findAdmin(province.properties.department_id)
    : query.department_id
      ? findAdmin(query.department_id)
      : null;
  const sentences: string[] = [];
  if (province && province.properties.level === "province") {
    const dept = department?.properties.name;
    sentences.push(
      dept
        ? `El análisis corresponde a la provincia ${province.properties.name}, en el departamento ${dept}.`
        : `El análisis corresponde a la provincia ${province.properties.name}.`,
    );
  } else if (department && department.properties.level === "department") {
    sentences.push(`El departamento señalado es ${department.properties.name}.`);
  }
  if (query.place) {
    sentences.push(
      `El lugar buscado es ${query.place.name} (${query.place.lat.toFixed(2)}, ${query.place.lon.toFixed(2)}).`,
    );
  }
  return sentences.length > 0 ? sentences.join(" ") : null;
}

function leadSentence(
  query: InvestigationQuery,
  statistics: TrendStat[],
  relations: LagRelation[],
  event: EventWindow | null,
  hotspots: Hotspot[],
  names: Record<string, string>,
  units: Record<string, string>,
): string {
  if (query.case_id === "drought") {
    if (!event) {
      return "Con las variables y el intervalo elegidos no aparece una racha de precipitación por debajo de lo habitual.";
    }
    const duration = `${event.duration} ${event.duration_unit === "years" ? "años" : "meses"}`;
    if (query.question_id === "recovery") {
      return `La racha seca va de ${event.start} a ${event.end} (${duration}). ${event.recovery_note ?? "No se ve una vuelta del NDVI al rango habitual dentro del intervalo."}`;
    }
    if (query.question_id === "vegetation") {
      const ndvi = relations.find((relation) => relation.response === "ndvi" || relation.driver === "ndvi");
      return `Entre ${event.start} y ${event.end} la precipitación queda por debajo de lo habitual. ${ndvi ? ndvi.sentence : "El NDVI no muestra un rezago claro respecto de las otras variables elegidas."}`;
    }
    return `La precipitación queda por debajo de lo habitual desde ${event.start} hasta ${event.end} (${duration}). La anomalía más baja es ${event.intensity.toFixed(1)} ${event.intensity_unit}. ${event.extent_count} de ${event.extent_total} zonas quedan por debajo de su nivel habitual.`;
  }

  if (query.case_id === "fire") {
    if (query.question_id === "hotspots") {
      if (hotspots.length === 0) {
        return "Esta respuesta no incluye focos activos. El mapa reserva el lugar para dibujarlos cuando el servidor los envíe.";
      }
      const dates = [...new Set(hotspots.map((hotspot) => hotspot.date))];
      const when = dates.length === 1 ? `en ${dates[0]}` : `entre ${dates[0]} y ${dates[dates.length - 1]}`;
      return `Hay ${hotspots.length} focos en la serie, ${when}. ${event ? `Coinciden con condiciones favorables de ${event.start} a ${event.end}.` : "No coinciden con una racha de condiciones favorables en las variables elegidas."} En demostración, esos focos no son una detección satelital.`;
    }
    if (!event) {
      return "No se juntan temperatura alta, suelo seco y viento fuerte en una racha, con las variables elegidas.";
    }
    const duration = `${event.duration} ${event.duration_unit === "years" ? "años" : "meses"}`;
    if (query.question_id === "after") {
      const ndvi = statistics.find((item) => item.variable === "ndvi");
      const after = ndvi
        ? `En todo el intervalo el NDVI ${slopePhrase(ndvi, units.ndvi ?? "índice")}.`
        : "El NDVI no está entre las variables elegidas, así que no hay un cambio de vegetación que mostrar.";
      return `Las condiciones favorables ocupan ${event.start} a ${event.end} (${duration}). ${after}`;
    }
    return `De ${event.start} a ${event.end} (${duration}) coinciden calor, suelo más seco y viento más fuerte. ${event.extent_count} de ${event.extent_total} zonas quedan por encima de su temperatura habitual.`;
  }

  if (query.question_id === "sequence") {
    return relations[0]?.sentence ?? "No aparece una sucesión temporal clara entre las variables elegidas.";
  }
  const significant = statistics.filter((item) => item.significant);
  if (significant.length === 0) {
    return "Ninguna variable elegida tiene una tendencia lineal significativa en este intervalo. La serie se muestra igual.";
  }
  return significant
    .map((item) => `${names[item.variable]} ${slopePhrase(item, units[item.variable] ?? "")}`)
    .join(" ");
}

function slopePhrase(stat: TrendStat, unit: string): string {
  const verb = stat.direction === "up" ? "sube" : stat.direction === "down" ? "baja" : "casi no cambia";
  const amount = `${Math.abs(stat.slope_per_decade).toFixed(2)} ${unit} por década`.trim();
  const verdict = stat.significant ? "El cambio es significativo." : "El cambio no es significativo.";
  const pText = formatP(stat.p_value);
  const pClause = pText.startsWith("<") ? `p ${pText}` : `p = ${pText}`;
  return `${verb} ${amount} (Mann-Kendall, ${pClause}). ${verdict}`;
}

function preferPrecedence(a: LagRelation, b: LagRelation): LagRelation {
  const lead = a.lag > 0 ? a : b.lag > 0 ? b : null;
  const other = lead === a ? b : lead === b ? a : null;
  if (lead && other && Math.abs(lead.r) >= Math.abs(other.r) - 0.08) return lead;
  return Math.abs(a.r) >= Math.abs(b.r) ? a : b;
}

function sequenceLabel(relations: LagRelation[], names: Record<string, string>): string {
  const lagged = relations.filter((relation) => relation.lag > 0);
  if (lagged.length === 0) return "Sin rezago entre las series más alineadas.";
  const starts = [...new Set(lagged.map((relation) => relation.driver))];
  const chains = starts.map((start) => growChain(start, lagged));
  chains.sort((a, b) => b.length - a.length);
  const chain = chains[0];
  if (!chain || chain.length < 2) {
    return `${names[lagged[0].driver]}, luego ${names[lagged[0].response]}`;
  }
  return chain.map((id) => names[id]).join(", luego ");
}

function growChain(start: VariableId, lagged: LagRelation[]): VariableId[] {
  const chain: VariableId[] = [start];
  let cursor = start;
  while (chain.length < 4) {
    const next = lagged
      .filter((relation) => relation.driver === cursor && !chain.includes(relation.response))
      .sort((a, b) => a.lag - b.lag || Math.abs(b.r) - Math.abs(a.r))[0];
    if (!next) break;
    chain.push(next.response);
    cursor = next.response;
  }
  return chain;
}

function stressed(variable: VariableId, value: number): boolean {
  if (variable === "precipitation") return value < -20;
  if (variable === "soil_moisture" || variable === "ndvi") return value < -0.04;
  if (variable === "temperature") return value > 0.75;
  return Math.abs(value) > 0.2;
}

function recoveryNote(byId: Map<VariableId, Series>, eventEnd: string): string | null {
  const precip = byId.get("precipitation");
  const ndvi = byId.get("ndvi");
  if (!precip) return null;
  const after = precip.points.filter((point) => point.date > eventEnd);
  const rain = after.find((point) => point.anomaly > 0);
  if (!rain) return "La precipitación no vuelve a su nivel habitual dentro del intervalo.";
  if (!ndvi) return `La precipitación vuelve a su nivel habitual en ${rain.date}. El NDVI no está seleccionado.`;
  const green = ndvi.points.find((point) => point.date >= rain.date && point.anomaly > -0.02);
  if (!green) return `La precipitación se recupera en ${rain.date}. El NDVI no vuelve a su rango habitual en el intervalo.`;
  return `La precipitación vuelve a su nivel habitual en ${rain.date}. El NDVI lo hace en ${green.date}.`;
}

function demoHotspots(event: EventWindow | null, query: InvestigationQuery): Hotspot[] {
  const date = event?.start ?? "2019-08";
  const province = query.province_id ? findAdmin(query.province_id) : null;
  if (province && province.properties.level === "province") {
    const points = sampleInside(province, 4).slice(1);
    while (points.length < 3) {
      const last = points[points.length - 1] ?? sampleInside(province, 1)[0];
      points.push({ lat: last.lat + 0.05, lon: last.lon - 0.05 });
    }
    return points.slice(0, 3).map((point) => ({
      lat: roundCoord(point.lat),
      lon: roundCoord(point.lon),
      date,
    }));
  }
  if (query.place) {
    const { lat, lon } = query.place;
    return [
      { lat: roundCoord(lat + 0.08), lon: roundCoord(lon + 0.1), date },
      { lat: roundCoord(lat - 0.1), lon: roundCoord(lon + 0.04), date },
      { lat: roundCoord(lat + 0.03), lon: roundCoord(lon - 0.12), date },
    ];
  }
  return [
    { lat: -17.9, lon: -62.6, date },
    { lat: -18.6, lon: -61.4, date },
    { lat: -19.8, lon: -63.2, date },
  ];
}

function roundCoord(value: number): number {
  return Math.round(value * 10000) / 10000;
}

interface Anchor {
  id: string;
  name: string;
  lat: number;
  lon: number;
  factor: number;
}

function focusVariable(query: InvestigationQuery): VariableId {
  if (query.case_id === "drought" && query.variables.includes("precipitation")) return "precipitation";
  if (query.case_id === "fire" && query.variables.includes("temperature")) return "temperature";
  return query.variables[0];
}

function longestRun(points: SeriesPoint[], test: (point: SeriesPoint) => boolean) {
  return longestFlagRun(
    points,
    points.map((point) => test(point)),
  );
}

function longestFlagRun(points: SeriesPoint[], flags: boolean[]) {
  let best: SeriesPoint[] = [];
  let current: SeriesPoint[] = [];
  flags.forEach((flag, index) => {
    if (flag) current.push(points[index]);
    else current = [];
    if (current.length > best.length) best = [...current];
  });
  if (best.length < 2) return null;
  return { points: best, start: best[0].date, end: best[best.length - 1].date };
}

function climatology(variable: VariableId, month: number): number {
  const wet = Math.cos(((month - 1) / 12) * Math.PI * 2);
  if (variable === "precipitation") return 90 + 75 * wet;
  if (variable === "temperature") return 23.5 + 3.2 * Math.sin(((month - 10) / 12) * Math.PI * 2);
  if (variable === "ndvi") return 0.48 + 0.16 * wet;
  if (variable === "soil_moisture") return 0.45 + 0.16 * wet;
  return 2.6 - 0.7 * wet;
}

function noise(variable: VariableId): number {
  if (variable === "precipitation") return 18;
  if (variable === "temperature") return 0.7;
  if (variable === "ndvi") return 0.04;
  if (variable === "soil_moisture") return 0.04;
  return 0.35;
}

function trendDrift(variable: VariableId): number {
  if (variable === "temperature") return 0.7;
  if (variable === "precipitation") return -10;
  if (variable === "ndvi") return -0.03;
  if (variable === "soil_moisture") return -0.03;
  return 0.15;
}

function eventPulse(variable: VariableId, index: number, center: number, width: number): number {
  const shape = pulse(index, center, width);
  if (variable === "precipitation") return -58 * shape;
  if (variable === "soil_moisture") return -0.16 * pulse(index, center + 1, width);
  if (variable === "ndvi") return -0.14 * pulse(index, center + 2, width);
  if (variable === "temperature") return 1.3 * shape;
  return 0;
}

function firePulse(variable: VariableId, index: number, center: number, width: number): number {
  const shape = pulse(index, center, width);
  if (variable === "temperature") return 1.6 * shape;
  if (variable === "soil_moisture") return -0.12 * shape;
  if (variable === "wind") return 1.1 * shape;
  if (variable === "ndvi") return -0.08 * pulse(index, center + 1, width);
  return 0;
}

function pulse(index: number, center: number, width: number): number {
  const distance = Math.abs(index - center);
  if (distance > width) return 0;
  return Math.cos((distance / width) * (Math.PI / 2));
}

function mean(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function round(value: number, variable: VariableId): number {
  const digits = variable === "precipitation" || variable === "temperature" ? 2 : 3;
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function formatP(value: number): string {
  if (!Number.isFinite(value)) return "n/d";
  if (value < 0.001) return "< 0.001";
  return value.toFixed(3);
}

function inWindow(date: string, start: string, end: string): boolean {
  if (start.length === 4) return date.slice(0, 4) >= start && date.slice(0, 4) <= end;
  return date >= start && date <= end;
}

function parseMonth(value: string): { year: number; month: number } {
  const [year, month] = value.split("-").map(Number);
  return { year, month: month || 1 };
}

function monthIndex(year: number, month: number): number {
  return year * 12 + (month - 1);
}

function addMonths(year: number, month: number, offset: number): { year: number; month: number } {
  const index = monthIndex(year, month) + offset;
  return { year: Math.floor(index / 12), month: (index % 12) + 1 };
}

function hashString(value: string): number {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function mulberry32(seed: number): () => number {
  let state = seed;
  return () => {
    state |= 0;
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
