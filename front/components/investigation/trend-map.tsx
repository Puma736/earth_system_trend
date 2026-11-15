"use client";

import { Skeleton } from "@mantine/core";
import dynamic from "next/dynamic";
import type { AdminFeature } from "@/lib/investigation/bolivia";
import type { Hotspot, MapCell, MapFocus, PlaceRef } from "@/lib/investigation/types";

const GeoMap = dynamic(() => import("@/components/investigation/geo-map").then((mod) => mod.GeoMap), {
  ssr: false,
  loading: () => <Skeleton height={420} radius="md" />,
});

export function TrendMap(props: {
  cells: MapCell[] | null;
  hotspots: Hotspot[];
  caption: string;
  province: AdminFeature | null;
  department: AdminFeature | null;
  place: PlaceRef | null;
  focus: MapFocus;
}) {
  return <GeoMap {...props} />;
}
