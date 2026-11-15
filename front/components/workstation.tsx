"use client";

import {
  Alert,
  Anchor,
  AppShell,
  Badge,
  Button,
  Grid,
  Group,
  Paper,
  SegmentedControl,
  Select,
  Skeleton,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { useMediaQuery } from "@mantine/hooks";
import Link from "next/link";
import { useState } from "react";
import { BridgePanel } from "@/components/bridge-panel";
import { DroughtBoard } from "@/components/drought-board";
import { HotspotsPanel } from "@/components/hotspots-panel";
import { LeadPanel } from "@/components/lead-panel";
import { MapPanel } from "@/components/map-panel";
import { MethodsPanel } from "@/components/methods-panel";
import { API_LABEL, api } from "@/lib/api";
import { seasonShort } from "@/lib/format";
import type { Catalog, YearValue } from "@/lib/types";
import { useResource } from "@/lib/use-resource";

// Valores iniciales: la estación seca y la humedad del suelo superficial (el puente más fuerte).
const DEFAULT_SEASON = "DRY";
const DEFAULT_INDICATOR = "GWETTOP";
// La pantalla de la rama velaxd (/investigation) trabaja con series simuladas, no con datos de la NASA.
const INVESTIGATION_LINK = "Investigation (simulated data)";

export function Workstation() {
  const health = useResource("health", (signal) => api.health(signal));
  const catalog = useResource("catalog", (signal) => api.catalog(signal));

  return (
    <AppShell
      header={{ height: 72 }}
      padding="sm"
      styles={{
        header: { background: "#151722", borderBottom: "1px solid #39383A" },
        main: { background: "#151722" },
      }}
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between" wrap="nowrap">
          <div>
            <Title order={1} size="h3" c="#CBD931">
              Trend Detective
            </Title>
            <Text size="sm" visibleFrom="md">
              Is the region drying out? Are fire hotspots increasing? How much, and is it a real change?
            </Text>
            <Anchor component={Link} href="/investigation" size="xs" c="#CBD931" hiddenFrom="md">
              {INVESTIGATION_LINK}
            </Anchor>
          </div>
          <Group gap="md" wrap="nowrap" style={{ flexShrink: 0 }}>
            <Anchor component={Link} href="/investigation" size="sm" c="#CBD931" visibleFrom="md">
              {INVESTIGATION_LINK}
            </Anchor>
            <Badge variant="dot" color={health.status === "ready" ? "signal" : "gray"} title={`API: ${API_LABEL}`}>
              {health.status === "ready" ? "API online" : health.status === "error" ? "API offline" : "Checking API"}
            </Badge>
          </Group>
        </Group>
      </AppShell.Header>
      <AppShell.Main>
        {catalog.data ? (
          <Dashboard catalog={catalog.data} />
        ) : catalog.status === "error" ? (
          <Alert variant="outline" color="indigo" title="Cannot load the regions from the API" maw={720}>
            <Stack gap="xs" align="flex-start">
              <Text size="sm">{catalog.error.message}</Text>
              <Text size="sm">Start the backend (see the README), then press Retry.</Text>
              <Button
                size="xs"
                variant="outline"
                color="gray"
                onClick={() => {
                  catalog.retry();
                  health.retry();
                }}
              >
                Retry
              </Button>
            </Stack>
          </Alert>
        ) : (
          <Stack gap="sm">
            <Skeleton height={92} radius="md" />
            <Skeleton height={420} radius="md" />
          </Stack>
        )}
      </AppShell.Main>
    </AppShell>
  );
}

function Dashboard({ catalog }: { catalog: Catalog }) {
  const narrow = useMediaQuery("(max-width: 48em)");
  const [regionId, setRegionId] = useState(catalog.regions[0]?.id ?? "");
  const [seasonId, setSeasonId] = useState(
    catalog.seasons.some((item) => item.id === DEFAULT_SEASON) ? DEFAULT_SEASON : (catalog.seasons[0]?.id ?? ""),
  );
  const [start, setStart] = useState(catalog.years.drought.start);
  const [end, setEnd] = useState(catalog.years.drought.end);
  const [indicator, setIndicator] = useState(
    catalog.indicators.some((item) => item.param === DEFAULT_INDICATOR)
      ? DEFAULT_INDICATOR
      : (catalog.indicators[0]?.param ?? ""),
  );
  const [pickedYear, setPickedYear] = useState<number | null>(null);

  const region = catalog.regions.find((item) => item.id === regionId) ?? catalog.regions[0];
  const season = catalog.seasons.find((item) => item.id === seasonId) ?? catalog.seasons[0];

  // Los focos solo existen desde 2003 (Terra + Aqua): su período es el elegido, recortado.
  const fireStart = Math.max(start, catalog.years.hotspots.start);
  const fireEnd = Math.min(end, catalog.years.hotspots.end);
  const fireValid = fireStart < fireEnd;
  const fireEmpty = fireValid
    ? null
    : `Hotspot records cover ${catalog.years.hotspots.start}–${catalog.years.hotspots.end}. Choose a period that ends after ${catalog.years.hotspots.start}.`;
  const area = { region: region.id, season: season.id };

  const drought = useResource(`drought|${area.region}|${area.season}|${start}|${end}`, (signal) =>
    api.drought({ ...area, start, end }, signal),
  );
  const hotspots = useResource(
    fireValid ? `hotspots|${area.region}|${area.season}|${fireStart}|${fireEnd}` : null,
    (signal) => api.hotspots({ ...area, start: fireStart, end: fireEnd }, signal),
  );
  const lead = useResource(
    fireValid ? `lead|${area.region}|${area.season}|${fireStart}|${fireEnd}` : null,
    (signal) => api.lead({ ...area, start: fireStart, end: fireEnd }, signal),
  );
  const link = useResource(
    fireValid ? `link|${area.region}|${area.season}|${indicator}|${fireStart}|${fireEnd}` : null,
    (signal) => api.link({ ...area, indicator, start: fireStart, end: fireEnd }, signal),
  );

  // El mapa abre en el año con más focos; un clic en una barra o en un punto lo cambia.
  const peakYear = maxYear(hotspots.data?.series ?? [], fireStart, fireEnd);
  const mapYear =
    pickedYear !== null && pickedYear >= fireStart && pickedYear <= fireEnd ? pickedYear : (peakYear ?? null);
  const grid = useResource(
    fireValid && mapYear !== null ? `grid|${area.region}|${area.season}|${mapYear}` : null,
    (signal) => api.hotspotGrid({ ...area, year: mapYear ?? fireEnd }, signal),
  );

  const droughtYears = range(catalog.years.drought.start, catalog.years.drought.end);
  const fireYears = fireValid ? range(fireStart, fireEnd) : [];

  return (
    <Stack gap="sm">
      <Paper p="md" component="section" aria-label="Filters">
        <Group gap="xl" align="flex-end" wrap="wrap">
          <div>
            <Text size="sm" fw={600} mb={6} id="region-label">
              Region
            </Text>
            <SegmentedControl
              aria-labelledby="region-label"
              color="signal"
              value={region.id}
              onChange={setRegionId}
              data={catalog.regions.map((item) => ({ value: item.id, label: item.name }))}
              orientation={narrow ? "vertical" : "horizontal"}
              fullWidth={narrow}
            />
          </div>
          <div>
            <Text size="sm" fw={600} mb={6} id="season-label">
              Season
            </Text>
            <SegmentedControl
              aria-labelledby="season-label"
              color="signal"
              value={season.id}
              onChange={setSeasonId}
              data={catalog.seasons.map((item) => ({ value: item.id, label: seasonShort(item) }))}
              orientation={narrow ? "vertical" : "horizontal"}
              fullWidth={narrow}
            />
          </div>
          <Group gap="xs" align="flex-end" wrap="nowrap">
            <Select
              label="From"
              data={droughtYears.filter((year) => year < end).map(String)}
              value={String(start)}
              onChange={(value) => value && setStart(Number(value))}
              allowDeselect={false}
              w={96}
            />
            <Select
              label="To"
              data={droughtYears.filter((year) => year > start).map(String)}
              value={String(end)}
              onChange={(value) => value && setEnd(Number(value))}
              allowDeselect={false}
              w={96}
            />
          </Group>
        </Group>
        <Text size="xs" mt="sm" c="dimmed">
          {season.name}. Drought data {catalog.years.drought.start}–{catalog.years.drought.end}; hotspots{" "}
          {catalog.years.hotspots.start}–{catalog.years.hotspots.end}. {region.note}
        </Text>
      </Paper>

      <DroughtBoard resource={drought} selectedYear={mapYear} />

      <Grid gutter="sm" align="stretch">
        <Grid.Col span={{ base: 12, lg: 5 }}>
          <HotspotsPanel
            resource={hotspots}
            selectedYear={mapYear}
            onPickYear={setPickedYear}
            emptyReason={fireEmpty}
          />
        </Grid.Col>
        <Grid.Col span={{ base: 12, lg: 7 }}>
          <MapPanel
            resource={grid}
            region={region}
            season={season}
            years={fireYears}
            year={mapYear}
            peakYear={peakYear}
            onPickYear={setPickedYear}
            emptyReason={fireEmpty}
          />
        </Grid.Col>
        <Grid.Col span={{ base: 12, lg: 7 }}>
          <Stack gap="sm">
            <BridgePanel
            resource={link}
            indicators={catalog.indicators}
            indicator={indicator}
            onIndicator={setIndicator}
            selectedYear={mapYear}
            onPickYear={setPickedYear}
            emptyReason={fireEmpty}
          />
            <LeadPanel resource={lead} emptyReason={fireEmpty} />
          </Stack>
        </Grid.Col>
        <Grid.Col span={{ base: 12, lg: 5 }}>
          <MethodsPanel region={region} hotspotStart={catalog.years.hotspots.start} />
        </Grid.Col>
      </Grid>
    </Stack>
  );
}

function range(first: number, last: number): number[] {
  return Array.from({ length: Math.max(0, last - first + 1) }, (_, index) => first + index);
}

function maxYear(series: YearValue[], first: number, last: number): number | null {
  let best: YearValue | null = null;
  for (const point of series) {
    if (point.year < first || point.year > last) continue;
    if (!best || point.value > best.value) best = point;
  }
  return best?.year ?? null;
}
