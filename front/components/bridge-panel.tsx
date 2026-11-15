"use client";

import { Group, Paper, Select, Skeleton, Stack, Text } from "@mantine/core";
import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";
import { AXIS_TICK, CHART, DataTable, PanelError, PanelHeader, TooltipCard } from "@/components/chart-kit";
import { formatCompact, formatCount, formatFixed, formatNumber, monthRange, pClause, unitLabel, withUnit } from "@/lib/format";
import type { IndicatorInfo, LinkResponse } from "@/lib/types";
import type { Resource } from "@/lib/use-resource";

interface Point {
  year: number;
  x: number;
  y: number;
}

export function BridgePanel({
  resource,
  indicators,
  indicator,
  onIndicator,
  selectedYear,
  onPickYear,
  emptyReason,
}: {
  resource: Resource<LinkResponse>;
  indicators: IndicatorInfo[];
  indicator: string;
  onIndicator: (param: string) => void;
  selectedYear: number | null;
  onPickYear: (year: number) => void;
  emptyReason: string | null;
}) {
  const { data, status } = resource;
  return (
    <Paper p="md" h="100%">
      <Stack gap="sm">
        <PanelHeader
          eyebrow="Drought vs. hotspots"
          title="Are drier years also fire years?"
          refreshing={status === "loading" && data !== null}
        />
        <Select
          label="Drought indicator"
          data={indicators.map((item) => ({ value: item.param, label: `${item.label} (${item.param})` }))}
          value={indicator}
          onChange={(value) => value && onIndicator(value)}
          allowDeselect={false}
          maw={360}
        />
        {emptyReason ? <Text size="sm">{emptyReason}</Text> : null}
        {resource.status === "error" ? <PanelError error={resource.error} onRetry={resource.retry} /> : null}
        {status === "loading" && data === null ? <Skeleton height={300} radius="md" /> : null}
        {data ? (
          <Stack gap="sm" className={status === "loading" ? "is-refreshing" : undefined}>
            <BridgeSummary data={data} />
            <BridgeChart data={data} selectedYear={selectedYear} onPickYear={onPickYear} />
            <Text size="xs">
              One dot per year, {monthRange(data.season.months)}. Click a dot to show that year on the map.
            </Text>
            <DataTable
              head={["Year", `${data.indicator_label} (${unitLabel(data.indicator_unit)})`, "Hotspots"]}
              rows={data.points.map((point) => [point.year, formatNumber(point.drought_value), formatCount(point.hotspots)])}
            />
          </Stack>
        ) : null}
      </Stack>
    </Paper>
  );
}

function BridgeSummary({ data }: { data: LinkResponse }) {
  const label = data.indicator_label.toLowerCase();
  return (
    <div>
      {data.rho !== null ? (
        <>
          <Group gap="sm" align="baseline" wrap="wrap">
            <Text className="stat-figure">ρ = {formatFixed(data.rho, 2)}</Text>
            <Text size="sm">
              {pClause("p", data.p_value)} · {data.n_years} years
            </Text>
          </Group>
          <Text size="sm" mt={4}>
            {data.rho < 0
              ? `Years with lower ${label} tended to have more hotspots.`
              : `Years with higher ${label} tended to have more hotspots.`}{" "}
            {data.p_value !== null && data.p_value < 0.05
              ? "The relationship is significant (p < 0.05)."
              : "The relationship is not significant (p ≥ 0.05)."}
          </Text>
        </>
      ) : (
        <Text size="sm">Fewer than 3 years in common: no correlation.</Text>
      )}
      <Text size="xs" mt={4} c="dimmed">
        {data.method}. {data.caveat}
      </Text>
    </div>
  );
}

function BridgeChart({
  data,
  selectedYear,
  onPickYear,
}: {
  data: LinkResponse;
  selectedYear: number | null;
  onPickYear: (year: number) => void;
}) {
  // El año elegido va al final para que se dibuje encima.
  const points: Point[] = data.points
    .map((point) => ({ year: point.year, x: point.drought_value, y: point.hotspots }))
    .sort((a, b) => Number(a.year === selectedYear) - Number(b.year === selectedYear));

  return (
    <div className="plot" style={{ height: 290 }}>
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 14, right: 18, bottom: 26, left: 8 }}>
          <CartesianGrid stroke={CHART.grid} />
          <XAxis
            type="number"
            dataKey="x"
            name={data.indicator_label}
            domain={["auto", "auto"]}
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={{ stroke: CHART.axis }}
            tickFormatter={(value: number) => formatNumber(value)}
            label={{
              value: `${data.indicator_label} (${unitLabel(data.indicator_unit)})`,
              position: "insideBottom",
              offset: -16,
              fill: CHART.text,
              fontSize: 11,
            }}
          />
          <YAxis
            type="number"
            dataKey="y"
            name="Hotspots"
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={false}
            width={52}
            allowDecimals={false}
            tickFormatter={(value: number) => formatCompact(value)}
            label={{ value: "Hotspots", angle: -90, position: "insideLeft", offset: 4, fill: CHART.text, fontSize: 11 }}
          />
          <Tooltip
            isAnimationActive={false}
            cursor={false}
            content={({ active, payload }) => {
              const point = active ? (payload?.[0]?.payload as Point | undefined) : undefined;
              if (!point) return null;
              return (
                <TooltipCard
                  title={String(point.year)}
                  rows={[
                    { label: "hotspots", value: formatCount(point.y) },
                    { label: data.indicator_label.toLowerCase(), value: withUnit(formatNumber(point.x), data.indicator_unit) },
                  ]}
                />
              );
            }}
          />
          <Scatter
            data={points}
            isAnimationActive={false}
            shape={(props: unknown) => <YearDot {...(props as DotProps)} selectedYear={selectedYear} />}
            onClick={(entry: unknown) => {
              const year = (entry as { payload?: Point } | undefined)?.payload?.year;
              if (typeof year === "number") onPickYear(year);
            }}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}

interface DotProps {
  cx?: number;
  cy?: number;
  payload?: Point;
}

/** Punto de 9 px con anillo del color del fondo y un área de clic de 24 px. */
function YearDot({ cx, cy, payload, selectedYear }: DotProps & { selectedYear: number | null }) {
  if (cx === undefined || cy === undefined || !payload) return <g />;
  const selected = payload.year === selectedYear;
  return (
    <g style={{ cursor: "pointer" }}>
      <circle cx={cx} cy={cy} r={12} fill="transparent" />
      <circle
        cx={cx}
        cy={cy}
        r={selected ? 6 : 4.5}
        fill={selected ? CHART.accent : CHART.context}
        stroke={CHART.surface}
        strokeWidth={2}
      />
      {selected ? (
        <text x={cx + 9} y={cy - 9} fill={CHART.text} fontSize={11} fontFamily={AXIS_TICK.fontFamily}>
          {payload.year}
        </text>
      ) : null}
    </g>
  );
}
