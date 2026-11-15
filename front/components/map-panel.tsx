"use client";

import { Group, Paper, Select, Stack, Text } from "@mantine/core";
import { CHART, DataTable, Key, PanelError, PanelHeader } from "@/components/chart-kit";
import { TrendMap } from "@/components/trend-map";
import { formatCount, formatLat, formatLon, monthRange } from "@/lib/format";
import { binLabel, HOTSPOT_BINS } from "@/lib/hotspot-scale";
import type { HotspotGridResponse, Region, Season } from "@/lib/types";
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
}) {
  const { data, status } = resource;
  const cells = data?.cells ?? [];
  const total = cells.reduce((sum, cell) => sum + cell.count, 0);
  const shownYear = data?.year ?? year;
  const period = `${monthRange(season.months)} ${shownYear ?? ""}`.trim();

  return (
    <Paper p="md" h="100%">
      <Stack gap="sm">
        <PanelHeader eyebrow="Map · hotspots per 0.5° cell" title="Where were the hotspots?" refreshing={status === "loading"}>
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
        {resource.status === "error" ? <PanelError error={resource.error} onRetry={resource.retry} /> : null}
        {data ? (
          <Text size="sm">
            <strong>{formatCount(total)}</strong> hotspots in {region.name}, {period}
            {shownYear !== null && shownYear === peakYear ? ", the year with the most hotspots" : ""}.
          </Text>
        ) : null}
        <div className={status === "loading" ? "is-refreshing" : undefined}>
          <TrendMap
            bbox={region.bbox}
            cells={cells}
            cellDeg={data?.cell_deg ?? 0.5}
            period={period}
            label={`Map of hotspots per cell in ${region.name}, ${period}`}
          />
        </div>
        <Group gap="md" wrap="wrap" role="list" aria-label="Map legend">
          {HOTSPOT_BINS.map((bin) => (
            <Group key={bin.min} gap={6} wrap="nowrap" role="listitem">
              <Key kind="rect" color={bin.color} />
              <Text size="xs">{binLabel(bin)}</Text>
            </Group>
          ))}
          <Group gap={6} wrap="nowrap" role="listitem">
            <Key kind="dashed" color={CHART.region} />
            <Text size="xs">Region rectangle</Text>
          </Group>
          <Group gap={6} wrap="nowrap" role="listitem">
            <Key kind="line" color={CHART.text} />
            <Text size="xs">Departments</Text>
          </Group>
        </Group>
        <Text size="xs" c="dimmed">
          {region.note} Boundaries: GeoBolivia (public domain). Tiles: © OpenStreetMap contributors.
        </Text>
        {data && cells.length > 0 ? (
          <DataTable
            head={["Cell center", "Hotspots"]}
            rows={[...cells]
              .sort((a, b) => b.count - a.count)
              .map((cell) => [`${formatLat(cell.lat)}, ${formatLon(cell.lon)}`, formatCount(cell.count)])}
          />
        ) : null}
      </Stack>
    </Paper>
  );
}
