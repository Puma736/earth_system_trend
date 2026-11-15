/** Colores de lectura. El calor es cálido; la sequía, fría. No entran en el cálculo. */
export type VariableRole = "heat" | "drought";

export interface VariableSwatch {
  param: string;
  label: string;
  role: VariableRole;
  color: string;
}

export const VARIABLE_SWATCHES: VariableSwatch[] = [
  { param: "T2M_MAX", label: "Maximum temperature", role: "heat", color: "#e07a3d" },
  { param: "PRECTOTCORR", label: "Rainfall", role: "drought", color: "#7eb6ff" },
  { param: "GWETTOP", label: "Surface soil moisture", role: "drought", color: "#3D4B97" },
  { param: "GWETROOT", label: "Root-zone soil moisture", role: "drought", color: "#9aa6e8" },
  { param: "EVPTRNS", label: "Evapotranspiration", role: "drought", color: "#6aa8b8" },
  { param: "RH2M", label: "Air humidity", role: "drought", color: "#8fd0c4" },
];

const byParam = new Map(VARIABLE_SWATCHES.map((item) => [item.param, item]));

export function variableColor(param: string): string {
  return byParam.get(param)?.color ?? "#A0A0A5";
}
