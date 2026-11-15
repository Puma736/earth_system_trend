import type { Catalog, InvestigationQuery, InvestigationResult } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Contrato del backend FastAPI:
 * GET  /health
 * GET  /catalog                 -> Catalog
 *   departments y provinces son opcionales; el mapa lee los limites locales.
 * POST /investigations          body InvestigationQuery -> InvestigationResult
 *   El cuerpo siempre incluye department_id, province_id y place.
 *   place es { name, lat, lon } o null. Los ids van en null si no hay seleccion.
 *
 * El navegador solo muestra la respuesta. Series, pruebas y conclusiones salen del servidor.
 */
export function dataSource(): "api" {
  return "api";
}

export async function fetchCatalog(): Promise<Catalog> {
  const response = await request("/catalog");
  return (await response.json()) as Catalog;
}

export async function runInvestigation(query: InvestigationQuery): Promise<InvestigationResult> {
  const response = await request(
    "/investigations",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(query),
    },
    120000,
  );
  const result = (await response.json()) as InvestigationResult;
  return { ...result, source: "api" };
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await request("/health", {}, 2500);
    return response.ok;
  } catch {
    return false;
  }
}

async function request(path: string, init: RequestInit = {}, timeoutMs = 8000): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...init,
      cache: "no-store",
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(`El servidor respondió ${response.status} en ${path}.`);
    }
    return response;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("El servidor no respondió a tiempo.");
    }
    if (error instanceof Error && error.message.startsWith("El servidor respondió")) throw error;
    throw new Error("No hay conexión con el servidor.");
  } finally {
    clearTimeout(timer);
  }
}
