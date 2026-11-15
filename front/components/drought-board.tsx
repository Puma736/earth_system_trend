"use client";

import { Box, Group, Paper, SimpleGrid, Skeleton, Stack, Text } from "@mantine/core";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import {
  AXIS_TICK,
  CHART,
  DataTable,
  LegendRow,
  PanelError,
  PanelHeader,
  ChangeNote,
  TooltipCard,
  VerdictBadge,
} from "@/components/chart-kit";
import {
  formatCount,
  formatNumber,
  formatSigma,
  formatSigned,
  monthRange,
  pClause,
  rankPhrase,
  unitLabel,
  withUnit,
} from "@/lib/format";
import type { DroughtIndicator, DroughtResponse, YearAnomaly } from "@/lib/types";
import type { Resource } from "@/lib/use-resource";

interface Row {
  year: number;
  value: number;
  trend: number | null;
  anomaly: YearAnomaly | null;
}

export function DroughtBoard({
  resource,
  selectedYear,
}: {
  resource: Resource<DroughtResponse>;
  /** Año elegido en las barras de focos o en el mapa. Si no está en la serie, se usa el último. */
  selectedYear: number | null;
}) {
  const { data, status } = resource;
  return (
    <Paper p="md">
      <Stack gap="md">
        <PanelHeader
          eyebrow={`Drought evidence · ${data?.source ?? "MERRA-2 via NASA POWER"}`}
          title="Is the region drying out?"
          refreshing={status === "loading" && data !== null}
        />
        {resource.status === "error" ? <PanelError error={resource.error} onRetry={resource.retry} /> : null}
        {status === "loading" && data === null ? <BoardSkeleton /> : null}
        {data ? (
          <Stack gap="md" className={status === "loading" ? "is-refreshing" : undefined}>
            <Summary data={data} />
            <LegendRow
              items={[
                { kind: "line", color: CHART.context, label: `Average for ${monthRange(data.season.months)}, per year` },
                ...(data.indicators.some((indicator) => indicator.trend !== null)
                  ? [{ kind: "line" as const, color: CHART.accent, label: "Sen trend line" }]
                  : []),
              ]}
            />
            <SimpleGrid cols={{ base: 1, sm: 2, xl: 3 }} spacing="sm" verticalSpacing="sm">
              {data.indicators.map((indicator) => (
                <IndicatorCard key={indicator.param} indicator={indicator} selectedYear={selectedYear} />
              ))}
            </SimpleGrid>
          </Stack>
        ) : null}
      </Stack>
    </Paper>
  );
}

function Summary({ data }: { data: DroughtResponse }) {
  const { summary } = data;
  // Sin ninguna tendencia, "0 of 6" se leería como evidencia en contra: se dice que falta período.
  const anyTrend = data.indicators.some((indicator) => indicator.trend !== null);
  return (
    <div>
      {anyTrend ? (
        <>
          <Group gap="lg" align="flex-end" wrap="wrap">
            <div className="hero-figure" aria-hidden="true">
              {summary.pointing_to_drying} of {summary.total}
            </div>
            <div>
              <Text fw={600} size="lg">
                indicators point to drying
              </Text>
              <Text size="sm">
                {summary.real_changes} of them {summary.real_changes === 1 ? "is a real change" : "are real changes"}{" "}
                (q &lt; 0.05).
              </Text>
            </div>
          </Group>
          <Text className="sr-only">{summary.text}</Text>
        </>
      ) : (
        <div>
          <Text fw={600} size="lg">
            No trends for {data.start}–{data.end}
          </Text>
          <Text size="sm">A trend needs at least 10 years. Choose a longer period.</Text>
        </div>
      )}
      <Text size="sm" mt="xs" c="dimmed">
        {data.region.name} · {data.season.name} · {data.start}–{data.end}
      </Text>
    </div>
  );
}

function IndicatorCard({ indicator, selectedYear }: { indicator: DroughtIndicator; selectedYear: number | null }) {
  const { trend, unit } = indicator;
  const byYear = new Map(indicator.anomalies.map((item) => [item.year, item]));
  const focus = (selectedYear !== null ? byYear.get(selectedYear) : undefined) ?? indicator.anomalies.at(-1);
  const first = indicator.series[0];
  const last = indicator.series[indicator.series.length - 1];
  const rows: Row[] = indicator.series.map((point) => ({
    year: point.year,
    value: point.value,
    // Recta de Sen: intercept es su valor en el primer año de la serie.
    trend: trend && first ? trend.intercept + (trend.slope_per_decade / 10) * (point.year - first.year) : null,
    anomaly: byYear.get(point.year) ?? null,
  }));

  return (
    <Box className="indicator-card" component="article" aria-label={indicator.label}>
      <Stack gap={6}>
        <Group justify="space-between" align="flex-start" wrap="nowrap" gap="xs">
          <div>
            <Text fw={600}>{indicator.label}</Text>
            <Text ff="monospace" size="xs" c="dimmed">
              {indicator.param}
            </Text>
          </div>
          <VerdictBadge verdict={indicator.verdict} />
        </Group>

        {trend ? (
          <div>
            <Text className="stat-figure">
              {withUnit(formatSigned(trend.slope_per_decade), unit)}
              <span className="stat-unit"> per decade</span>
            </Text>
            <Text size="xs">
              95% range {formatSigned(trend.slope_low_per_decade)} to {formatSigned(trend.slope_high_per_decade)} ·{" "}
              {trend.q_value !== null ? pClause("q", trend.q_value) : pClause("p", trend.p_value)}
            </Text>
          </div>
        ) : (
          <Text size="sm">Fewer than 10 years in this period, so there is no trend.</Text>
        )}

        <Text size="xs" fw={600}>
          <Direction indicator={indicator} />
        </Text>

        {focus && indicator.baseline ? (
          <Text size="xs">
            <strong>{focus.year}</strong>: {formatSigma(focus.z)} vs {indicator.baseline.start}–{indicator.baseline.end}
            {isRain(indicator) && focus.percent_of_normal !== null
              ? `, ${formatCount(focus.percent_of_normal)}% of normal`
              : ""}{" "}
            · {rankPhrase(focus.rank, indicator.rank_of, indicator.rank_by)}
          </Text>
        ) : null}

        <IndicatorChart rows={rows} unit={unit} rankOf={indicator.rank_of} rankBy={indicator.rank_by} />

        {trend && first && last ? (
          <Text size="xs">
            Change {first.year}–{last.year} along the trend line: {withUnit(formatSigned(trend.total_change), unit)}
          </Text>
        ) : null}
        <Text size="xs" c="dimmed">
          {indicator.definition} Unit: {unitLabel(unit)}.
        </Text>
        <ChangeNote trend={trend} format={(value) => withUnit(formatNumber(value), unit)} />
        {trend?.notes.map((note) => (
          <Text key={note} size="xs" className="method-note">
            {note}
          </Text>
        ))}
        <DataTable
          head={["Year", `Value (${unitLabel(unit)})`, "Trend line", "Anomaly", "Rank"]}
          rows={rows.map((row) => [
            row.year,
            formatNumber(row.value),
            row.trend === null ? "" : formatNumber(row.trend),
            row.anomaly ? formatSigma(row.anomaly.z) : "",
            row.anomaly ? `${row.anomaly.rank} / ${indicator.rank_of}` : "",
          ])}
        />
      </Stack>
    </Box>
  );
}

/** En la lluvia, "% de lo normal" se entiende mejor que las desviaciones estándar. */
function isRain(indicator: DroughtIndicator): boolean {
  return indicator.param === "PRECTOTCORR";
}

function Direction({ indicator }: { indicator: DroughtIndicator }) {
  const slope = indicator.trend?.slope_per_decade ?? 0;
  const arrow = slope > 0 ? "▲" : slope < 0 ? "▼" : "■";
  if (indicator.points_to_drying === null) return <>No trend computed</>;
  return (
    <>
      <span aria-hidden="true">{arrow} </span>
      {slope > 0 ? "Rising" : slope < 0 ? "Falling" : "Flat"}:{" "}
      {indicator.points_to_drying ? "points to drying" : "points away from drying"}
    </>
  );
}

function IndicatorChart({
  rows,
  unit,
  rankOf,
  rankBy,
}: {
  rows: Row[];
  unit: string;
  rankOf: number;
  rankBy: "lowest" | "highest";
}) {
  const first = rows[0]?.year ?? 0;
  const last = rows[rows.length - 1]?.year ?? 0;
  const decades = rows.map((row) => row.year).filter((year) => year % 10 === 0);
  const ticks = decades.length >= 2 ? decades : [first, last];

  return (
    <div className="plot" style={{ height: 136 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 8, right: 10, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={CHART.grid} vertical={false} />
          <XAxis
            dataKey="year"
            type="number"
            domain={[first, last]}
            ticks={ticks}
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={{ stroke: CHART.axis }}
            allowDecimals={false}
          />
          <YAxis
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={false}
            width={42}
            domain={["auto", "auto"]}
            tickCount={3}
            tickFormatter={(value: number) => formatNumber(value)}
          />
          <Tooltip
            isAnimationActive={false}
            cursor={{ stroke: CHART.axis, strokeWidth: 1 }}
            content={({ active, payload }) => {
              const row = active ? (payload?.[0]?.payload as Row | undefined) : undefined;
              if (!row) return null;
              return (
                <TooltipCard
                  title={String(row.year)}
                  rows={[
                    { label: "season average", value: withUnit(formatNumber(row.value), unit), color: CHART.context },
                    ...(row.trend === null
                      ? []
                      : [{ label: "trend line", value: withUnit(formatNumber(row.trend), unit), color: CHART.accent }]),
                    ...(row.anomaly
                      ? [
                          { label: "vs normal", value: formatSigma(row.anomaly.z) },
                          { label: `${rankBy} of ${rankOf} years`, value: `#${row.anomaly.rank}` },
                        ]
                      : []),
                  ]}
                />
              );
            }}
          />
          <Line
            type="linear"
            dataKey="value"
            stroke={CHART.context}
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 4, fill: CHART.context, stroke: CHART.surface, strokeWidth: 2 }}
            isAnimationActive={false}
          />
          <Line
            type="linear"
            dataKey="trend"
            stroke={CHART.accent}
            strokeWidth={2}
            dot={false}
            activeDot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function BoardSkeleton() {
  return (
    <Stack gap="sm">
      <Skeleton height={56} width="60%" />
      <SimpleGrid cols={{ base: 1, sm: 2, xl: 3 }} spacing="sm">
        {Array.from({ length: 6 }, (_, index) => (
          <Skeleton key={index} height={300} radius="md" />
        ))}
      </SimpleGrid>
      <Text size="xs">The first request for a region downloads from NASA POWER and can take up to a minute.</Text>
    </Stack>
  );
}
