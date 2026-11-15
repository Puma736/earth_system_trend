"use client";

import { Group, Paper, Skeleton, Stack, Text } from "@mantine/core";
import { Bar, CartesianGrid, Cell, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
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
  formatCompact,
  formatCount,
  formatPercent,
  formatSigma,
  formatSigned,
  monthRange,
  pClause,
  rankPhrase,
} from "@/lib/format";
import type { HotspotsResponse, YearAnomaly } from "@/lib/types";
import type { Resource } from "@/lib/use-resource";

interface Row {
  year: number;
  hotspots: number;
  trend: number | null;
  anomaly: YearAnomaly | null;
}

export function HotspotsPanel({
  resource,
  selectedYear,
  onPickYear,
  emptyReason,
}: {
  resource: Resource<HotspotsResponse>;
  selectedYear: number | null;
  onPickYear: (year: number) => void;
  /** Por qué no se pidió nada (por ejemplo, un período antes de 2003). */
  emptyReason: string | null;
}) {
  const { data, status } = resource;
  return (
    <Paper p="md" h="100%">
      <Stack gap="sm">
        <PanelHeader
          eyebrow="Fire hotspots · NASA FIRMS (MODIS)"
          title="More hotspots than before?"
          refreshing={status === "loading" && data !== null}
        />
        {emptyReason ? <Text size="sm">{emptyReason}</Text> : null}
        {resource.status === "error" ? <PanelError error={resource.error} onRetry={resource.retry} /> : null}
        {status === "loading" && data === null ? <Skeleton height={300} radius="md" /> : null}
        {data ? (
          <Stack gap="sm" className={status === "loading" ? "is-refreshing" : undefined}>
            <HotspotsSummary data={data} selectedYear={selectedYear} />
            <LegendRow
              items={[
                { kind: "rect", color: CHART.bar, label: `Hotspots, ${monthRange(data.season.months)}` },
                { kind: "line", color: CHART.accent, label: "Sen trend line" },
                { kind: "rect", color: CHART.context, label: "Year on the map" },
              ]}
            />
            <HotspotsChart data={data} selectedYear={selectedYear} onPickYear={onPickYear} />
            <Text size="xs">Click a bar to show that year on the map. Source: {data.source}.</Text>
            <DataTable
              head={["Year", "Hotspots", "Trend line"]}
              rows={toRows(data).map((row) => [
                row.year,
                formatCount(row.hotspots),
                row.trend === null ? "" : formatCount(row.trend),
              ])}
            />
          </Stack>
        ) : null}
      </Stack>
    </Paper>
  );
}

function HotspotsSummary({ data, selectedYear }: { data: HotspotsResponse; selectedYear: number | null }) {
  const { trend } = data;
  const focus =
    (selectedYear !== null ? data.anomalies.find((item) => item.year === selectedYear) : undefined) ??
    data.anomalies.at(-1);
  return (
    <div>
      <Group gap="sm" align="center" wrap="wrap">
        <VerdictBadge verdict={data.verdict} />
        {data.percent_change !== null ? (
          <Text className="stat-figure">
            {formatPercent(data.percent_change)}
            <span className="stat-unit">
              {" "}
              over {data.start}–{data.end}
            </span>
          </Text>
        ) : null}
      </Group>
      {trend ? (
        <Text size="xs" mt={4}>
          {formatSigned(trend.slope_per_decade)} hotspots per decade (95% range {formatSigned(trend.slope_low_per_decade)}{" "}
          to {formatSigned(trend.slope_high_per_decade)}) · {pClause("p", trend.p_value)} · {trend.n_years} years
        </Text>
      ) : (
        <Text size="xs" mt={4}>
          Fewer than 10 years in this period, so there is no trend.
        </Text>
      )}
      {focus && data.baseline ? (
        <Text size="xs" mt={4}>
          <strong>{focus.year}</strong>: {formatSigma(focus.z)} vs the {data.baseline.start}–{data.baseline.end} average
          · {rankPhrase(focus.rank, data.rank_of, data.rank_by)}
        </Text>
      ) : null}
      <ChangeNote trend={trend} format={formatCount} />
      {trend?.notes.map((note) => (
        <Text key={note} size="xs" className="method-note">
          {note}
        </Text>
      ))}
    </div>
  );
}

function toRows(data: HotspotsResponse): Row[] {
  const { trend } = data;
  const first = data.series[0]?.year ?? data.start;
  return data.series.map((point) => ({
    year: point.year,
    hotspots: point.value,
    trend: trend ? trend.intercept + (trend.slope_per_decade / 10) * (point.year - first) : null,
    anomaly: data.anomalies.find((item) => item.year === point.year) ?? null,
  }));
}

function HotspotsChart({
  data,
  selectedYear,
  onPickYear,
}: {
  data: HotspotsResponse;
  selectedYear: number | null;
  onPickYear: (year: number) => void;
}) {
  const rows = toRows(data);
  return (
    <div className="plot" style={{ height: 260 }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart
          data={rows}
          margin={{ top: 10, right: 12, bottom: 0, left: 0 }}
          barCategoryGap={2}
          onClick={(state) => {
            const year = Number(state?.activeLabel);
            if (Number.isFinite(year)) onPickYear(year);
          }}
        >
          <CartesianGrid stroke={CHART.grid} vertical={false} />
          <XAxis
            dataKey="year"
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={{ stroke: CHART.axis }}
            interval="preserveStartEnd"
            minTickGap={12}
          />
          <YAxis
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={false}
            width={44}
            allowDecimals={false}
            tickFormatter={(value: number) => formatCompact(value)}
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
                    { label: "hotspots", value: formatCount(row.hotspots), color: CHART.bar, kind: "rect" },
                    ...(row.trend === null
                      ? []
                      : [{ label: "trend line", value: formatCount(row.trend), color: CHART.accent }]),
                    ...(row.anomaly
                      ? [
                          { label: "vs average", value: formatSigma(row.anomaly.z) },
                          { label: `${data.rank_by} of ${data.rank_of} years`, value: `#${row.anomaly.rank}` },
                        ]
                      : []),
                  ]}
                />
              );
            }}
          />
          <Bar dataKey="hotspots" maxBarSize={24} radius={[4, 4, 0, 0]} isAnimationActive={false} cursor="pointer">
            {rows.map((row) => (
              <Cell key={row.year} fill={row.year === selectedYear ? CHART.context : CHART.bar} />
            ))}
          </Bar>
          <Line
            type="linear"
            dataKey="trend"
            stroke={CHART.accent}
            strokeWidth={2}
            dot={false}
            activeDot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
