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

const nextConfig: NextConfig = {
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
