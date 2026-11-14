import { territoryIndex } from "./bolivia";
import type { Catalog } from "./types";

const territory = territoryIndex();

export const demoCatalog: Catalog = {
  regions: [
    { id: "bolivia", name: "Bolivia", lat: -16.5, lon: -64.5 },
    { id: "la_paz", name: "La Paz", lat: -16.5, lon: -68.15 },
    { id: "cochabamba", name: "Cochabamba", lat: -17.39, lon: -66.16 },
    { id: "santa_cruz", name: "Santa Cruz", lat: -17.78, lon: -63.18 },
    { id: "beni", name: "Beni", lat: -14.83, lon: -64.9 },
    { id: "chaco", name: "Chaco", lat: -20.04, lon: -63.52 },
  ],
  variables: [
    {
      id: "precipitation",
      code: "P",
      name: "Precipitación",
      unit: "mm",
      definition: "Agua que llega a la superficie en el mes.",
      source: "NASA POWER PRECTOTCORR",
    },
    {
      id: "temperature",
      code: "T2M",
      name: "Temperatura",
      unit: "°C",
      definition: "Temperatura del aire a 2 m.",
      source: "NASA POWER T2M",
    },
    {
      id: "ndvi",
      code: "NDVI",
      name: "NDVI",
      unit: "índice",
      definition: "Verdor de la vegetación. Valores más altos, cubierta más activa.",
      source: "MODIS NDVI",
    },
    {
      id: "soil_moisture",
      code: "HS",
      name: "Humedad del suelo",
      unit: "fracción",
      definition: "Agua en la zona de raíces, como fracción del suelo.",
      source: "MERRA-2 GWETROOT",
    },
    {
      id: "wind",
      code: "V",
      name: "Viento",
      unit: "m/s",
      definition: "Velocidad del viento a 2 m.",
      source: "NASA POWER WS2M",
    },
  ],
  cases: [
    {
      id: "drought",
      label: "Sequía",
      variables: ["precipitation", "soil_moisture", "ndvi", "temperature"],
      questions: [
        { id: "onset", text: "Inicio y duración de la sequía" },
        { id: "extent", text: "Intensidad y extensión" },
        { id: "vegetation", text: "Deterioro de la vegetación" },
        { id: "recovery", text: "Recuperación después de las lluvias" },
      ],
    },
    {
      id: "fire",
      label: "Incendios",
      variables: ["temperature", "soil_moisture", "ndvi", "wind"],
      questions: [
        { id: "dry", text: "Zonas con condiciones de sequedad" },
        { id: "evolution", text: "Evolución de condiciones favorables" },
        { id: "hotspots", text: "Focos activos" },
        { id: "after", text: "Cambios posteriores al incendio" },
      ],
    },
    {
      id: "open",
      label: "Libre",
      variables: ["temperature", "precipitation"],
      questions: [
        { id: "trend", text: "Qué cambia, dónde, cuánto y si es significativo" },
        { id: "sequence", text: "Qué variable precede a otra" },
      ],
    },
  ],
  departments: territory.departments,
  provinces: territory.provinces,
};

export const CAVEAT =
  "Las anomalías restan el valor habitual de cada mes, así que el ciclo estacional no entra en la tendencia. El orden en el tiempo no demuestra causalidad: no controla uso del suelo, riego ni otros forzantes.";
