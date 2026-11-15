"use client";

import { Box, Group, Paper, Select, Stack, Text } from "@mantine/core";
import { useMemo } from "react";
import { CHART, DataTable, Key, PanelError, PanelHeader } from "@/components/chart-kit";
import { TrendMap } from "@/components/trend-map";
import { featureCovers, type DepartmentFeature } from "@/lib/bolivia";
import { formatCount, formatLat, formatLon, monthRange } from "@/lib/format";
import { HOTSPOT_BINS } from "@/lib/hotspot-scale";
import { VARIABLE_SWATCHES } from "@/lib/variable-colors";
import type { HotspotCell, HotspotGridResponse, Region, Season } from "@/lib/types";
import type { Resource } from "@/lib/use-resource";

export function MapPanel({
  resource,
  region,
  season,
  years,
  year,
  peakYear,
  onPickYear,
  emptyReason,
  selected,
  available,
  areaNote,
}: {
  resource: Resource<HotspotGridResponse>;
  region: Region;
  season: Season;
  years: number[];
  year: number | null;
  /** Año con más focos del período: es el que se muestra si nadie eligió otro. */
  peakYear: number | null;
  onPickYear: (year: number) => void;
  emptyReason: string | null;
  selected: DepartmentFeature[];
  available: DepartmentFeature[];
  areaNote?: string;
}) {
  const { data, status, error } = resource;
  const cells: HotspotCell[] = data?.cells ?? [];
  const visible = useMemo(
    () => cells.filter((cell) => selected.some((feature) => featureCovers(feature, cell.lon, cell.lat))),
    [cells, selected],
  );
  const context = useMemo(
    () => available.filter((feature) => !selected.some((item) => item.properties.id === feature.properties.id)),
    [available, selected],
  );
  const total = visible.reduce((sum, cell) => sum + cell.count, 0);
  const shownYear = data?.year ?? year;
  const period = `${monthRange(season.months)} ${shownYear ?? ""}`.trim();
  const where = territoryPhrase(selected, available, region.name);

  return (
    <Paper p="md" h="100%">
      <Stack gap="sm">
        <PanelHeader eyebrow="Map · hotspots" title="Where were the hotspots?" refreshing={status === "loading"}>
          <Select
            aria-label="Year on the map"
            data={years.map(String)}
            value={year === null ? null : String(year)}
            onChange={(value) => value && onPickYear(Number(value))}
            allowDeselect={false}
            disabled={years.length === 0}
            w={96}
            size="xs"
          />
        </PanelHeader>
        {emptyReason ? <Text size="sm">{emptyReason}</Text> : null}
        {selected.length === 0 ? <Text size="sm">Choose one or more provinces in Region to see them here.</Text> : null}
        {status === "error" && error ? <PanelError error={error} onRetry={resource.retry} /> : null}
        {data && selected.length > 0 ? (
          <Text size="sm">
            <strong>{formatCount(total)}</strong> hotspots inside {where}, {period}
            {shownYear !== null && shownYear === peakYear ? ", the year with the most hotspots" : ""}. Each square is
            the 0.5° cell the count was totaled in, drawn from its center. Red is fire hotspots only.
          </Text>
        ) : null}
        <div className={status === "loading" && !data ? "is-refreshing" : undefined}>
          <TrendMap
            bbox={region.bbox}
            cells={cells}
            cellDeg={data?.cell_deg ?? 0.5}
            cellDegLat={data?.cell_deg ?? 0.5}
            cellDegLon={data?.cell_deg ?? 0.5}
            period={period}
            label={selected.length > 0 ? `Hotspots inside ${where}, ${period}` : `Map of hotspots in ${region.name}`}
            selected={selected}
            context={context}
          />
        </div>
        <ColorKey contextCount={context.length} />
        <Text size="xs" c="dimmed">
          {areaNote ?? region.note} Boundaries: GeoBolivia (public domain). Tiles: © OpenStreetMap contributors.
        </Text>
        {data && visible.length > 0 ? (
          <DataTable
            head={["Cell center", "Hotspots"]}
            rows={[...visible]
              .sort((a, b) => b.count - a.count)
              .map((cell) => [`${formatLat(cell.lat)}, ${formatLon(cell.lon)}`, formatCount(cell.count)])}
          />
        ) : null}
      </Stack>
    </Paper>
  );
}

const HOTSPOT_COLOR: Record<number, string> = {
  1: "Pale pink: 1–24 fire detections in that square.",
  25: "Salmon: 25–99 fire detections.",
  100: "Red: 100–249 fire detections.",
  250: "Dark red: 250–999 fire detections.",
  1000: "Deep red: 1,000 or more fire detections, the most.",
};

const CHART_COLOR: Record<string, string> = {
  PRECTOTCORR: "Light blue",
  GWETTOP: "Blue",
  GWETROOT: "Pale blue",
  EVPTRNS: "Teal",
  RH2M: "Mint",
};

function ColorKey({ contextCount }: { contextCount: number }) {
  const heat = VARIABLE_SWATCHES.filter((item) => item.role === "heat");
  const drought = VARIABLE_SWATCHES.filter((item) => item.role === "drought");
  return (
    <Box className="color-key" component="section" aria-label="Color key">
      <Text className="eyebrow">Color key</Text>
      <Text size="sm" mt="xs">
        Each sample below is the color on the screen and what it stands for. A darker red square means more fire
        detections. The number inside the square is that count.
      </Text>
      <Text size="xs" fw={600} mt="sm">
        Heat, on the map
      </Text>
      <Stack gap={4} mt={6} role="list">
        {HOTSPOT_BINS.map((bin) => (
          <Group key={bin.min} gap={8} wrap="nowrap" role="listitem">
            <Key kind="rect" color={bin.color} />
            <Text size="sm">{HOTSPOT_COLOR[bin.min]}</Text>
          </Group>
        ))}
        {heat.map((item) => (
          <Group key={item.param} gap={8} wrap="nowrap" role="listitem">
            <Key kind="line" color={item.color} />
            <Text size="sm">Orange line: {item.label.toLowerCase()} in the charts, not a square on the map.</Text>
          </Group>
        ))}
      </Stack>
      <Text size="xs" fw={600} mt="sm">
        Drought, in the charts
      </Text>
      <Stack gap={4} mt={6} role="list">
        {drought.map((item) => (
          <Group key={item.param} gap={8} wrap="nowrap" role="listitem">
            <Key kind="line" color={item.color} />
            <Text size="sm">
              {CHART_COLOR[item.param]} line: {item.label.toLowerCase()} in the charts above the map.
            </Text>
          </Group>
        ))}
      </Stack>
      <Text size="xs" fw={600} mt="sm">
        Lines on the map
      </Text>
      <Stack gap={4} mt={6} role="list">
        <Group gap={8} wrap="nowrap" role="listitem">
          <span className="key-frame" aria-hidden="true" />
          <Text size="sm">Thin dark frame: the edge of one 0.5° square.</Text>
        </Group>
        <Group gap={8} wrap="nowrap" role="listitem">
          <Key kind="line" color="#f6f8d4" />
          <Text size="sm">White line: the border of the selected province. Color stops at this line.</Text>
        </Group>
        <Group gap={8} wrap="nowrap" role="listitem">
          <Key kind="line" color={CHART.text} />
          <Text size="sm">Gray line: the border of a department.</Text>
        </Group>
        {contextCount > 0 ? (
          <Group gap={8} wrap="nowrap" role="listitem">
            <Key kind="line" color={CHART.accent} />
            <Text size="sm">Yellow-green line: the other provinces of this department.</Text>
          </Group>
        ) : null}
      </Stack>
      <Text size="sm" mt="sm">
        Open ground inside the white line had no detections in this season. Land past that line is the next department,
        or another country.
      </Text>
      <Text size="xs" c="dimmed" mt={6}>
        Zoom with the wheel while the pointer is on the map. The count appears inside a square once it is large enough.
      </Text>
    </Box>
  );
}

function territoryPhrase(selected: DepartmentFeature[], available: DepartmentFeature[], regionName: string): string {
  if (selected.length === 0) return "the selected provinces";
  if (selected.length === available.length) return regionName;
  const names = selected.map((feature) => feature.properties.name);
  if (names.length === 1) return names[0];
  if (names.length === 2) return `${names[0]} and ${names[1]}`;
  if (names.length === 3) return `${names[0]}, ${names[1]} and ${names[2]}`;
  return `${names.length} provinces`;
}
