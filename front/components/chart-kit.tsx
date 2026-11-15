"use client";

import { Alert, Badge, Button, Group, Loader, Stack, Table, Text, Title } from "@mantine/core";
import type { ReactNode } from "react";
import type { ApiError } from "@/lib/api";
import { pClause } from "@/lib/format";
import type { Trend, Verdict } from "@/lib/types";

/**
 * Colores de las gráficas: la paleta del proyecto (theme.ts) sobre el fondo #151722.
 * Gris para el dato, "signal" para la tendencia; separación para daltonismo validada.
 */
export const CHART = {
  surface: "#151722",
  grid: "#39383A",
  axis: "#6d6d72",
  text: "#A0A0A5",
  context: "#A0A0A5",
  bar: "#6d6d72",
  accent: "#CBD931",
  region: "#9aa2d4",
} as const;

export const AXIS_TICK = {
  fill: CHART.text,
  fontSize: 11,
  fontFamily: '"IBM Plex Mono", Consolas, monospace',
};

type KeyKind = "line" | "dashed" | "rect" | "dot";

export function Key({ kind, color }: { kind: KeyKind; color: string }) {
  if (kind === "line" || kind === "dashed") {
    return (
      <svg width="18" height="10" aria-hidden="true">
        <line
          x1="1"
          y1="5"
          x2="17"
          y2="5"
          stroke={color}
          strokeWidth="2"
          strokeLinecap="round"
          strokeDasharray={kind === "dashed" ? "4 3" : undefined}
        />
      </svg>
    );
  }
  if (kind === "dot") {
    return (
      <svg width="10" height="10" aria-hidden="true">
        <circle cx="5" cy="5" r="4" fill={color} />
      </svg>
    );
  }
  return (
    <svg width="12" height="10" aria-hidden="true">
      <rect x="1" y="1" width="10" height="8" rx="2" fill={color} />
    </svg>
  );
}

export function LegendRow({ items }: { items: { kind: KeyKind; color: string; label: string }[] }) {
  return (
    <Group gap="md" wrap="wrap" role="list" aria-label="Legend">
      {items.map((item) => (
        <Group key={item.label} gap={6} wrap="nowrap" role="listitem">
          <Key kind={item.kind} color={item.color} />
          <Text size="xs">{item.label}</Text>
        </Group>
      ))}
    </Group>
  );
}

export interface TooltipRow {
  label: string;
  value: string;
  color?: string;
  kind?: KeyKind;
}

/** Tooltip de las gráficas: el valor primero, el nombre después. */
export function TooltipCard({ title, rows }: { title: string; rows: TooltipRow[] }) {
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip-title">{title}</div>
      {rows.map((row) => (
        <div key={row.label} className="chart-tooltip-row">
          {row.color ? <Key kind={row.kind ?? "line"} color={row.color} /> : null}
          <strong>{row.value}</strong>
          <span>{row.label}</span>
        </div>
      ))}
    </div>
  );
}

/** La tabla con los mismos valores de la gráfica, para no depender del tooltip. */
export function DataTable({ head, rows }: { head: string[]; rows: (string | number)[][] }) {
  return (
    <details className="data-table">
      <summary>Data table</summary>
      <div className="data-table-scroll">
        <Table withRowBorders={false} verticalSpacing={2} fz="xs">
          <Table.Thead>
            <Table.Tr>
              {head.map((cell) => (
                <Table.Th key={cell}>{cell}</Table.Th>
              ))}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {rows.map((row, index) => (
              <Table.Tr key={index}>
                {row.map((cell, column) => (
                  <Table.Td key={column}>{cell}</Table.Td>
                ))}
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </div>
    </details>
  );
}

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  if (verdict === "Real change") {
    return (
      <Badge color="signal" variant="filled">
        Real change
      </Badge>
    );
  }
  return (
    <Badge color="gray" variant={verdict === "Not yet certain" ? "outline" : "light"}>
      {verdict}
    </Badge>
  );
}

export function PanelHeader({
  eyebrow,
  title,
  refreshing,
  children,
}: {
  eyebrow: string;
  title: string;
  refreshing?: boolean;
  children?: ReactNode;
}) {
  return (
    <Group justify="space-between" align="flex-start" gap="sm">
      <div>
        <Text className="eyebrow">{eyebrow}</Text>
        <Title order={2} size="h4" mt={2}>
          {title}
        </Title>
      </div>
      <Group gap="xs" align="center">
        {refreshing ? <Loader size="xs" color="signal" aria-label="Updating" /> : null}
        {children}
      </Group>
    </Group>
  );
}

export function PanelError({ error, onRetry }: { error: ApiError; onRetry: () => void }) {
  const pending = error.status === 503;
  return (
    <Alert variant="outline" color={pending ? "indigo" : "gray"} title={errorTitle(error)}>
      <Stack gap="xs" align="flex-start">
        <Text size="sm">{error.message}</Text>
        {pending ? (
          <Text size="xs">
            The hotspot counts appear once the backend has backend/data/firms_monthly_cells.csv
            (generated by scripts/download_firms.py).
          </Text>
        ) : null}
        <Button size="xs" variant="outline" color="gray" onClick={onRetry}>
          Retry
        </Button>
      </Stack>
    </Alert>
  );
}

function errorTitle(error: ApiError): string {
  if (error.status === 503) return "Hotspot data pending";
  if (error.status === 502) return "NASA POWER did not answer";
  if (error.kind === "network") return "API unreachable";
  if (error.kind === "timeout") return "The API is taking too long";
  return "The request was rejected";
}

/** "Level shift in 2012": solo si Pettitt da p < 0.05. Una tendencia pareja también parece un salto. */
export function ChangeNote({ trend, format }: { trend: Trend | null; format: (value: number) => string }) {
  if (!trend || trend.change_year === null || trend.change_p_value === null || trend.change_p_value >= 0.05) return null;
  return (
    <Text size="xs">
      Level shift from {trend.change_year}: average {format(trend.change_mean_before ?? 0)} before,{" "}
      {format(trend.change_mean_after ?? 0)} after ({pClause("p", trend.change_p_value)}, Pettitt). A steady trend can
      also look like a shift.
    </Text>
  );
}
