import type { NextConfig } from "next";

/**
 * node_modules vive en otro disco (enlace). path.relative entre C: y G:
 * devuelve una ruta absoluta y Next le antepone "./", que webpack no resuelve.
 * Si la dependencia está en el mismo disco, la ruta relativa se deja igual.
 */
function repairCrossDriveSpecifier(value: unknown): unknown {
  if (typeof value === "string") {
    const normalized = value.replace(/\\/g, "/");
    const absolute = normalized.match(/^\.\/([A-Za-z]:\/.*)$/);
    return absolute ? absolute[1] : value;
  }
  if (Array.isArray(value)) return value.map(repairCrossDriveSpecifier);
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    const next: Record<string, unknown> = {};
    for (const [key, item] of Object.entries(record)) {
      next[key] = repairCrossDriveSpecifier(item);
    }
    return next;
  }
  return value;
}

/**
 * El navegador pide /api/* y /health a este mismo servidor y Next.js los reenvía al
 * backend. Así, desde otra computadora de la red solo hace falta el puerto 3000, no
 * importa la IP de esta máquina y el backend puede escuchar solo en 127.0.0.1.
 * BACKEND_URL se lee al arrancar npm run dev (y en el build).
 */
const BACKEND_URL = (process.env.BACKEND_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` },
      { source: "/health", destination: `${BACKEND_URL}/health` },
    ];
  },
  experimental: {
    // La primera consulta de una región sin caché tarda hasta ~50 s (NASA POWER) y el
    // proxy corta a los 30 s por defecto. Va por encima de los 120 s del cliente.
    proxyTimeout: 130_000,
  },
  webpack: (config) => {
    const current = config.entry as unknown;
    if (typeof current === "function") {
      config.entry = ((...args: unknown[]) =>
        Promise.resolve((current as (...input: unknown[]) => unknown)(...args)).then(
          repairCrossDriveSpecifier,
        )) as typeof config.entry;
    }
    return config;
  },
};

export default nextConfig;
