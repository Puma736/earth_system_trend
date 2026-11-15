import { List, Paper, Stack, Text, Title } from "@mantine/core";
import type { Region } from "@/lib/types";

export function MethodsPanel({
  region,
  areaNote,
  hotspotStart,
}: {
  region: Region;
  areaNote?: string;
  hotspotStart: number;
}) {
  return (
    <Paper p="md" h="100%">
      <Stack gap="sm">
        <div>
          <Text className="eyebrow">Methods &amp; limits</Text>
          <Title order={2} size="h4" mt={2}>
            How to read these results
          </Title>
        </div>
        <List size="sm" spacing="xs">
          <List.Item>
            <strong>Trend:</strong> Mann-Kendall test with the Hamed-Rao correction for autocorrelation. The rate is the
            Sen slope per decade, with its 95% range. A linear regression runs only as a control, and a note appears
            when the two methods disagree.
          </List.Item>
          <List.Item>
            <strong>&quot;Real change&quot;</strong> means q &lt; 0.05 for the drought indicators (p-values corrected for
            testing 6 indicators, Benjamini-Hochberg) and p &lt; 0.05 for hotspots. &quot;Not enough data&quot; means
            fewer than 10 years.
          </List.Item>
          <List.Item>
            <strong>One source:</strong> the 6 drought indicators all come from the MERRA-2 reanalysis (via NASA POWER),
            so they are not 6 independent proofs.
          </List.Item>
          <List.Item>
            <strong>Approximate area:</strong> {areaNote ?? region.note}
          </List.Item>
          <List.Item>
            <strong>Seasons:</strong> the months of the dry season and of the burning peak are still to be confirmed.
          </List.Item>
          <List.Item>
            <strong>A hotspot is not burned area.</strong> Many are agricultural burns, clouds and smoke can hide fires,
            and the Terra and Aqua satellites are drifting in orbit, which can affect recent counts. Counts start in{" "}
            {hotspotStart}, the first full year with both satellites.
          </List.Item>
          <List.Item>
            <strong>Relationship, not proof of cause:</strong> fires also depend on human burning, deforestation and
            policies.
          </List.Item>
        </List>
      </Stack>
    </Paper>
  );
}
