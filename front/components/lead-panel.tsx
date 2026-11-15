"use client";

import { Paper, Skeleton, Stack, Table, Text } from "@mantine/core";
import { PanelError, PanelHeader, VerdictBadge } from "@/components/chart-kit";
import { formatFixed, monthRange, pClause } from "@/lib/format";
import type { LeadResponse } from "@/lib/types";
import type { Resource } from "@/lib/use-resource";

/** ¿La época húmeda anterior (oct-mar) anticipa los focos? Un solo desfase, con FDR (/api/lead). */
export function LeadPanel({ resource, emptyReason }: { resource: Resource<LeadResponse>; emptyReason: string | null }) {
  const { data, status } = resource;
  return (
    <Paper p="md">
      <Stack gap="sm">
        <PanelHeader
          eyebrow="One season ahead"
          title="Does the wet season before predict the hotspots?"
          refreshing={status === "loading" && data !== null}
        />
        {emptyReason ? <Text size="sm">{emptyReason}</Text> : null}
        {resource.status === "error" ? <PanelError error={resource.error} onRetry={resource.retry} /> : null}
        {status === "loading" && data === null ? <Skeleton height={220} radius="md" /> : null}
        {data ? (
          <Stack gap="xs" className={status === "loading" ? "is-refreshing" : undefined}>
            <Text size="sm">
              Each indicator averaged over the wet season that ends in March (Oct of the year before to Mar), against
              the hotspots of {monthRange(data.season.months)} that same year, {data.start}–{data.end}.
            </Text>
            <Table withRowBorders={false} verticalSpacing={4} fz="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Wet-season indicator</Table.Th>
                  <Table.Th>ρ</Table.Th>
                  <Table.Th>q</Table.Th>
                  <Table.Th>Verdict</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {data.items.map((item) => (
                  <Table.Tr key={item.param}>
                    <Table.Td>{item.label}</Table.Td>
                    <Table.Td ff="monospace">{item.rho === null ? "n/a" : formatFixed(item.rho, 2)}</Table.Td>
                    <Table.Td ff="monospace">{item.q_value === null ? "n/a" : pClause("q", item.q_value)}</Table.Td>
                    <Table.Td>
                      <VerdictBadge verdict={item.verdict} />
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
            <Text size="xs" c="dimmed">
              One lag, fixed in advance (not the best of many), Spearman, and q corrected for testing 6 indicators.{" "}
              {data.caveat}
            </Text>
          </Stack>
        ) : null}
      </Stack>
    </Paper>
  );
}
