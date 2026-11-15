import type {
  Catalog,
  DroughtResponse,
  HotspotGridResponse,
  HotspotsResponse,
  PlaceGridResponse,
  LeadResponse,
  LinkResponse,
} from "./types";

/**
 * Adónde llama el navegador (ver .env.example).
 * - Vacío, lo normal: al mismo origen de la página (/api/..., /health) y el servidor de
 *   Next.js lo reenvía a BACKEND_URL. Funciona igual desde otra computadora y sin CORS.
 * - Con NEXT_PUBLIC_API_URL: directo a esa URL; el backend debe aceptar el origen en CORS.
 */
export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/+$/, "");

/** Cómo nombrar el destino en los mensajes. */
export const API_LABEL = API_URL || "the Next.js server, which forwards /api to BACKEND_URL";

export type ApiErrorKind = "http" | "network" | "timeout";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly kind: ApiErrorKind,
    readonly status: number | null = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface AreaQuery {
  region: string;
  season: string;
  /** Ids de provincia separados por coma. Vacío: el rectángulo de la región. */
  provinces?: string;
}

export interface PeriodQuery extends AreaQuery {
  start: number;
  end: number;
}

type Params = Record<string, string | number>;

// La primera consulta de una región sin caché descarga de NASA POWER: ~10 s, y ~50 s para Bolivia.
const POWER_TIMEOUT_MS = 120_000;
const FIRMS_TIMEOUT_MS = 30_000;

export const api = {
  health: (signal?: AbortSignal) => getJson<{ status: string }>("/health", {}, signal, 4_000),
  catalog: (signal?: AbortSignal) => getJson<Catalog>("/api/regions", {}, signal, 15_000),
  drought: (query: PeriodQuery, signal?: AbortSignal) =>
    getJson<DroughtResponse>("/api/drought", { ...query }, signal, POWER_TIMEOUT_MS),
  hotspots: (query: PeriodQuery, signal?: AbortSignal) =>
    getJson<HotspotsResponse>("/api/hotspots", { ...query }, signal, FIRMS_TIMEOUT_MS),
  hotspotGrid: (query: AreaQuery & { year: number }, signal?: AbortSignal) =>
    getJson<HotspotGridResponse>("/api/hotspots/grid", { ...query }, signal, FIRMS_TIMEOUT_MS),
  placeGrid: (query: { season: string; year: number }, signal?: AbortSignal) =>
    getJson<PlaceGridResponse>("/api/hotspots/places", { ...query }, signal, POWER_TIMEOUT_MS),
  link: (query: PeriodQuery & { indicator: string }, signal?: AbortSignal) =>
    getJson<LinkResponse>("/api/link", { ...query }, signal, POWER_TIMEOUT_MS),
  lead: (query: PeriodQuery, signal?: AbortSignal) =>
    getJson<LeadResponse>("/api/lead", { ...query }, signal, POWER_TIMEOUT_MS),
};

export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

async function getJson<T>(path: string, params: Params, signal: AbortSignal | undefined, timeoutMs: number): Promise<T> {
  // Con API_URL vacío la ruta es relativa a la página; con una URL completa, la base se ignora.
  const url = new URL(`${API_URL}${path}`, typeof window === "undefined" ? "http://localhost" : window.location.href);
  for (const [key, value] of Object.entries(params)) url.searchParams.set(key, String(value));

  // Un solo controlador para la cancelación del llamador y para el tiempo límite.
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);
  const cancel = () => controller.abort();
  if (signal?.aborted) controller.abort();
  signal?.addEventListener("abort", cancel, { once: true });

  try {
    // Sin cabeceras propias: así el navegador no hace preflight de CORS.
    const response = await fetch(url, { signal: controller.signal, cache: "no-store" });
    if (!response.ok) {
      const detail = await errorDetail(response);
      if (detail !== null) throw new ApiError(detail, "http", response.status);
      // Los errores del backend siempre vienen en JSON. Un 5xx sin JSON es el proxy de
      // Next.js diciendo que el backend no responde (apagado o en otro puerto).
      if (response.status >= 500) {
        throw new ApiError(
          `The backend did not answer (HTTP ${response.status}). Check that it is running${
            API_URL ? ` at ${API_URL}` : " and that BACKEND_URL in front/.env.local points to it"
          }.`,
          "network",
          response.status,
        );
      }
      throw new ApiError(
        `The API answered ${response.status}${response.statusText ? ` ${response.statusText}` : ""}.`,
        "http",
        response.status,
      );
    }
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (timedOut) {
      throw new ApiError(`The API did not answer within ${Math.round(timeoutMs / 1000)} s.`, "timeout");
    }
    if (isAbortError(error)) throw error;
    throw new ApiError(`Cannot reach ${API_LABEL}.`, "network");
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", cancel);
  }
}

/**
 * El mensaje de error del backend: {"detail": "..."}, o {"detail": [{msg}]} en las
 * validaciones de FastAPI. null si la respuesta no trae ese JSON.
 */
async function errorDetail(response: Response): Promise<string | null> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail) return body.detail;
    if (Array.isArray(body.detail)) {
      const messages = body.detail
        .map((item) => (item && typeof item === "object" && "msg" in item ? String(item.msg) : ""))
        .filter(Boolean);
      if (messages.length > 0) return messages.join("; ");
    }
  } catch {
    // La respuesta no era JSON.
  }
  return null;
}
