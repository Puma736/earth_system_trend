"use client";

import { Alert, AppShell, Badge, Button, Group, Paper, SimpleGrid, Skeleton, Stack, Text, Title } from "@mantine/core";
import Link from "next/link";
import { NalixNav } from "@/components/nalix-nav";
import { api } from "@/lib/api";
import type { Region } from "@/lib/types";
import { useResource } from "@/lib/use-resource";

const REGION_COPY: Record<string, { name: string; note: string }> = {
  santa_cruz: {
    name: "Departamento de Santa Cruz",
    note: "Rectángulo aproximado: también incluye partes de Beni, Chuquisaca, Brasil y Paraguay.",
  },
  chiquitania: {
    name: "Chiquitanía",
    note: "Rectángulo aproximado, subregión de Santa Cruz.",
  },
  bolivia: {
    name: "Bolivia",
    note: "Contexto del país. El rectángulo es más ancho que 10 grados.",
  },
};

export function RegionsBoard() {
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
          <Title order={1} size="h3" c="#CBD931">
            Nalix
          </Title>
          <NalixNav />
        </Group>
      </AppShell.Header>
      <AppShell.Main>
        <Stack gap="sm" maw={960}>
          <div>
            <p className="eyebrow">Regiones</p>
            <Title order={2} size="h3" mt={6} c="#e6e6ea">
              Dónde mira Nalix
            </Title>
            <Text mt={6}>
              Cada región es el rectángulo con el que se leen la sequía y los focos de calor. Elige una
              para abrir su análisis.
            </Text>
          </div>
          {catalog.status === "error" ? (
            <Alert variant="outline" color="indigo" title="No se pudieron cargar las regiones">
              <Stack gap="xs" align="flex-start">
                <Text size="sm">{catalog.error.message}</Text>
                <Button size="xs" variant="outline" color="gray" onClick={catalog.retry}>
                  Reintentar
                </Button>
              </Stack>
            </Alert>
          ) : catalog.data ? (
            <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="sm">
              {catalog.data.regions.map((region) => (
                <RegionCard key={region.id} region={region} />
              ))}
            </SimpleGrid>
          ) : (
            <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="sm">
              <Skeleton height={180} radius="md" />
              <Skeleton height={180} radius="md" />
              <Skeleton height={180} radius="md" />
            </SimpleGrid>
          )}
        </Stack>
      </AppShell.Main>
    </AppShell>
  );
}

function RegionCard({ region }: { region: Region }) {
  const copy = REGION_COPY[region.id];
  return (
    <Paper p="md" h="100%">
      <Stack gap="xs" h="100%">
        <Badge variant="outline" color="gray">
          {region.id}
        </Badge>
        <Title order={3} size="h4" c="#e6e6ea">
          {copy?.name ?? region.name}
        </Title>
        <Text size="sm" style={{ flex: 1 }}>
          {copy?.note ?? region.note}
        </Text>
        <Button component={Link} href={`/analisis?region=${region.id}`} size="xs" mt="sm">
          Ver análisis
        </Button>
      </Stack>
    </Paper>
  );
}
