"use client";

import { Skeleton } from "@mantine/core";
import dynamic from "next/dynamic";
import type { GeoMapProps } from "@/components/geo-map";

// Leaflet necesita window: el mapa se carga solo en el navegador.
const GeoMap = dynamic(() => import("@/components/geo-map").then((mod) => mod.GeoMap), {
  ssr: false,
  loading: () => <Skeleton height={420} radius="md" />,
});

export function TrendMap(props: GeoMapProps) {
  return <GeoMap {...props} />;
}
