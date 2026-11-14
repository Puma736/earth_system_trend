"use client";

import { LineChart } from "@mantine/charts";
import {
  Alert,
  AppShell,
  Badge,
  Box,
  Button,
  Checkbox,
  Grid,
  Group,
  Paper,
  Radio,
  SegmentedControl,
  Select,
  Skeleton,
  Stack,
  SimpleGrid,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { useEffect, useMemo, useState } from "react";
import { PlaceSearch } from "@/components/place-search";
import { TrendMap } from "@/components/trend-map";
import { checkHealth, dataSource, fetchCatalog, runInvestigation } from "@/lib/api";
import { findAdmin, territoryIndex } from "@/lib/bolivia";
import type {
  Aggregation,
  CaseId,
  Catalog,
  InvestigationResult,
  MapFocus,
  PlaceRef,
  VariableId,
} from "@/lib/types";

const YEARS = Array.from({ length: 24 }, (_, index) => String(2001 + index));

const SERIES_STYLE: Record<VariableId, { color: string; strokeDasharray?: string }> = {
  precipitation: { color: "#CBD931" },
  temperature: { color: "#A0A0A5" },
  ndvi: { color: "#CBD931", strokeDasharray: "5 4" },
  soil_moisture: { color: "#A0A0A5", strokeDasharray: "2 3" },
  wind: { color: "#CBD931", strokeDasharray: "1 3" },
};

type Scale = "z" | "value";
type Status = "idle" | "loading" | "ready" | "error";

export function Workstation() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [health, setHealth] = useState<"checking" | "up" | "down">("checking");
  const [regionId, setRegionId] = useState("bolivia");
  const [caseId, setCaseId] = useState<CaseId>("drought");
  const [questionId, setQuestionId] = useState("onset");
  const [variables, setVariables] = useState<VariableId[]>([
    "precipitation",
    "soil_moisture",
    "ndvi",
    "temperature",
  ]);
  const [startYear, setStartYear] = useState("2001");
  const [endYear, setEndYear] = useState("2024");
  const [aggregation, setAggregation] = useState<Aggregation>("monthly");
  const [scale, setScale] = useState<Scale>("z");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<InvestigationResult | null>(null);
  const [departmentId, setDepartmentId] = useState<string | null>(null);
  const [provinceId, setProvinceId] = useState<string | null>(null);
  const [place, setPlace] = useState<PlaceRef | null>(null);
  const [focus, setFocus] = useState<MapFocus>({ kind: "bolivia" });
  const territory = useMemo(() => territoryIndex(), []);

  useEffect(() => {
    let active = true;
    fetchCatalog()
      .then((next) => {
        if (!active) return;
        setCatalog(next);
        const first = next.cases[0];
        if (first) {
          setCaseId(first.id);
          setQuestionId(first.questions[0]?.id ?? "");
          setVariables(first.variables);
        }
        if (next.regions[0]) setRegionId(next.regions[0].id);
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setCatalogError(reason instanceof Error ? reason.message : "No se pudo leer el catálogo.");
      });
    checkHealth().then((ok) => {
      if (active) setHealth(ok ? "up" : "down");
    });
    return () => {
      active = false;
    };
  }, []);

  const activeCase = catalog?.cases.find((item) => item.id === caseId) ?? null;
  const names = useMemo(
    () => new Map(catalog?.variables.map((item) => [item.id, item.name]) ?? []),
    [catalog],
  );

  const chartRows = useMemo(() => {
    if (!result) return [];
    const shown =
      scale === "value"
        ? result.series.filter((item) => item.variable === result.map_variable)
        : result.series;
    const length = shown[0]?.points.length ?? 0;
    return Array.from({ length }, (_, index) => {
      const row: Record<string, string | number> = { date: shown[0].points[index].date };
      for (const series of shown) {
        const point = series.points[index];
        row[series.variable] = scale === "value" ? point.value : Number(point.z.toFixed(2));
      }
      return row;
    });
  }, [result, scale]);

  const chartSeries = useMemo(() => {
    if (!result) return [];
    const shown =
      scale === "value"
        ? result.series.filter((item) => item.variable === result.map_variable)
        : result.series;
    return shown.map((series) => ({
      name: series.variable,
      label: names.get(series.variable) ?? series.variable,
      color: scale === "value" ? "#CBD931" : SERIES_STYLE[series.variable].color,
      strokeDasharray: scale === "value" ? undefined : SERIES_STYLE[series.variable].strokeDasharray,
    }));
  }, [names, result, scale]);

  async function investigate() {
    if (variables.length === 0 || startYear > endYear) return;
    setStatus("loading");
    setError(null);
    try {
      const next = await runInvestigation({
        region_id: regionId,
        case_id: caseId,
        question_id: questionId,
        variables,
        start: `${startYear}-01`,
        end: `${endYear}-12`,
        aggregation,
        department_id: departmentId,
        province_id: provinceId,
        place,
      });
      setResult(next);
      setStatus("ready");
    } catch (reason: unknown) {
      setStatus("error");
      setError(reason instanceof Error ? reason.message : "No se pudo completar la investigación.");
    }
  }

  function changeCase(value: string) {
    const next = catalog?.cases.find((item) => item.id === value);
    if (!next) return;
    setCaseId(next.id);
    setVariables(next.variables);
    setQuestionId(next.questions[0]?.id ?? "");
  }

  const rangeInvalid = startYear > endYear;
  const sourceLabel = dataSource() === "api" ? "Servidor" : "Demostración";
  const departmentFeature = findAdmin(departmentId);
  const provinceFeature =
    findAdmin(provinceId)?.properties.department_id === departmentId ? findAdmin(provinceId) : null;
  const departmentOptions = territory.departments.map((item) => ({ value: item.id, label: item.name }));
  const provinceOptions = territory.provinces
    .filter((item) => item.department_id === departmentId)
    .map((item) => ({ value: item.id, label: item.name }));

  function chooseDepartment(value: string | null) {
    setDepartmentId(value);
    setProvinceId(null);
    setFocus(value ? { kind: "department", id: value } : { kind: "bolivia" });
  }

  function chooseProvince(value: string | null) {
    setProvinceId(value);
    if (value) setFocus({ kind: "province", id: value });
    else if (departmentId) setFocus({ kind: "department", id: departmentId });
    else setFocus({ kind: "bolivia" });
  }

  function choosePlace(next: PlaceRef | null) {
    setPlace(next);
    if (next) setFocus({ kind: "place", name: next.name, lat: next.lat, lon: next.lon });
  }

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
        <Group h="100%" px="md" justify="space-between">
          <div>
            <Title order={1} size="h3" c="#CBD931">
              Detective de tendencias
            </Title>
            <Text size="sm">Qué cambia, dónde, cuánto y si es significativo.</Text>
          </div>
          <Group gap="xs">
            <Badge variant="outline" color="gray">
              {sourceLabel}
            </Badge>
            <Badge variant="dot" color={health === "up" ? "signal" : "gray"}>
              {health === "checking"
                ? "Comprobando servidor"
                : health === "up"
                  ? "Servidor en línea"
                  : "Servidor sin respuesta"}
            </Badge>
          </Group>
        </Group>
      </AppShell.Header>
      <AppShell.Main>
        {catalogError ? (
          <Alert variant="outline" color="indigo" title="Catálogo">
            {catalogError}
          </Alert>
        ) : null}
        <Grid gutter="sm" align="stretch">
          <Grid.Col span={{ base: 12, lg: 3 }}>
            <Paper p="md" className="panel-scroll">
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  void investigate();
                }}
              >
                <Stack gap="md">
                  <Select
                    label="Región"
                    data={catalog?.regions.map((region) => ({ value: region.id, label: region.name })) ?? []}
                    value={regionId}
                    onChange={(value) => value && setRegionId(value)}
                    allowDeselect={false}
                    disabled={!catalog}
                  />
                  <div>
                    <Text size="sm" fw={600} mb={6}>
                      Qué quieres saber
                    </Text>
                    <SegmentedControl
                      fullWidth
                      value={caseId}
                      onChange={changeCase}
                      data={catalog?.cases.map((item) => ({ value: item.id, label: item.label })) ?? []}
                      color="signal"
                    />
                    <Radio.Group
                      value={questionId}
                      onChange={setQuestionId}
                      mt="sm"
                      aria-label="Pregunta"
                    >
                      <Stack gap={6}>
                        {activeCase?.questions.map((question) => (
                          <Radio key={question.id} value={question.id} label={question.text} color="signal" />
                        ))}
                      </Stack>
                    </Radio.Group>
                  </div>
                  <Checkbox.Group
                    label="Variables"
                    value={variables}
                    onChange={(value) => setVariables(value as VariableId[])}
                  >
                    <Stack gap="xs" mt="xs">
                      {catalog?.variables.map((variable) => (
                        <Checkbox
                          key={variable.id}
                          value={variable.id}
                          color="signal"
                          label={
                            <Group gap={6} wrap="nowrap">
                              <Text ff="monospace" size="xs" c="#CBD931">
                                {variable.code}
                              </Text>
                              <Text size="sm">{variable.name}</Text>
                            </Group>
                          }
                          description={`${variable.definition} ${variable.source}.`}
                        />
                      ))}
                    </Stack>
                  </Checkbox.Group>
                  <Group grow>
                    <Select
                      label="Desde"
                      data={YEARS}
                      value={startYear}
                      onChange={(value) => value && setStartYear(value)}
                      allowDeselect={false}
                    />
                    <Select
                      label="Hasta"
                      data={YEARS}
                      value={endYear}
                      onChange={(value) => value && setEndYear(value)}
                      allowDeselect={false}
                    />
                  </Group>
                  {rangeInvalid ? (
                    <Text size="sm">El inicio tiene que ser anterior al final.</Text>
                  ) : null}
                  <div>
                    <Text size="sm" fw={600} mb={6}>
                      Agregación
                    </Text>
                    <SegmentedControl
                      fullWidth
                      color="signal"
                      value={aggregation}
                      onChange={(value) => setAggregation(value as Aggregation)}
                      data={[
                        { value: "monthly", label: "Mensual" },
                        { value: "annual", label: "Anual" },
                      ]}
                    />
                  </div>
                  <Box className="run-action">
                    <Button
                      id="run-investigation"
                      type="submit"
                      color="signal"
                      fullWidth
                      loading={status === "loading"}
                      disabled={!catalog || variables.length === 0 || rangeInvalid}
                    >
                      Investigar
                    </Button>
                  </Box>
                  {variables.length === 0 ? (
                    <Text size="sm">Elige al menos una variable.</Text>
                  ) : null}
                </Stack>
              </form>
            </Paper>
          </Grid.Col>
          <Grid.Col span={{ base: 12, lg: 5 }}>
            <Paper p="md" h="100%">
              <Stack gap="sm" h="100%">
                <Text className="eyebrow">Mapa</Text>
                <Text size="sm">Dirección y magnitud</Text>
                {territory.problem ? (
                  <Text size="sm">{territory.problem}</Text>
                ) : null}
                <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="xs">
                  <Select
                    id="department-select"
                    label="Departamento"
                    placeholder="Elige un departamento"
                    size="sm"
                    data={departmentOptions}
                    value={departmentId}
                    onChange={chooseDepartment}
                    searchable
                    clearable
                    nothingFoundMessage="Sin departamentos"
                  />
                  <Select
                    id="province-select"
                    label="Provincia"
                    placeholder={departmentId ? "Elige una provincia" : "Primero elige un departamento"}
                    size="sm"
                    data={provinceOptions}
                    value={provinceFeature ? provinceId : null}
                    onChange={chooseProvince}
                    disabled={!departmentId}
                    searchable
                    clearable
                    nothingFoundMessage="Sin provincias en este departamento"
                  />
                </SimpleGrid>
                <PlaceSearch place={place} onPlace={choosePlace} />
                <Text size="sm">
                  {provinceFeature
                    ? `Provincia ${provinceFeature.properties.name}${departmentFeature ? `, ${departmentFeature.properties.name}` : ""}.`
                    : departmentFeature
                      ? `Departamento ${departmentFeature.properties.name}. Elige una provincia de este departamento.`
                      : "Bolivia. Elige departamento y, dentro, una provincia."}
                </Text>
                <TrendMap
                  cells={result?.map_cells ?? null}
                  hotspots={result?.hotspots ?? []}
                  caption={result?.map_caption ?? "Mapa de Bolivia sin una investigación todavía."}
                  province={provinceFeature}
                  department={departmentFeature}
                  place={place}
                  focus={focus}
                />
                <Text size="sm">
                  {result
                    ? result.map_caption
                    : "El mapa se llena al investigar. Cada círculo es una zona."}
                </Text>
                <Group gap="lg">
                  <LegendSwatch tone="high" label="Por encima de lo habitual" />
                  <LegendSwatch tone="low" label="Por debajo de lo habitual" />
                  {result?.hotspots.length ? <LegendSwatch tone="hot" label="Foco" /> : null}
                  {place ? <LegendSwatch tone="place" label="Lugar buscado" /> : null}
                </Group>
                <Text size="xs">Límites: GeoBolivia, dominio público. Teselas: OpenStreetMap.</Text>
                <Text size="sm" ff="monospace">
                  {result?.sequence_label ?? "La secuencia aparece junto a la conclusión."}
                </Text>
              </Stack>
            </Paper>
          </Grid.Col>
          <Grid.Col span={{ base: 12, lg: 4 }}>
            <Paper p="md" className="panel-scroll">
              <Stack gap="md">
                <Group justify="space-between" align="end">
                  <div>
                    <Text className="eyebrow">Análisis y escalas</Text>
                    <Text size="sm">
                      Comparada usa anomalías estandarizadas. Unidad propia muestra una variable.
                    </Text>
                  </div>
                </Group>
                <SegmentedControl
                  color="signal"
                  value={scale}
                  onChange={(value) => setScale(value as Scale)}
                  data={[
                    { value: "z", label: "Comparada" },
                    { value: "value", label: "Unidad propia" },
                  ]}
                />
                {status === "error" ? (
                  <Box className="notice" role="alert">
                    <Text fw={600}>La investigación no se completó</Text>
                    <Text size="sm">{error}</Text>
                  </Box>
                ) : null}
                {status === "loading" && !result ? (
                  <Skeleton height={260} />
                ) : null}
                {status === "idle" && !result ? (
                  <Box className="plot-empty">
                    <Text>Elige región, pregunta y variables. Luego investiga.</Text>
                  </Box>
                ) : null}
                {result && chartRows.length > 0 ? (
                  <Box className="plot">
                    <LineChart
                      h={260}
                      data={chartRows}
                      dataKey="date"
                      series={chartSeries}
                      curveType="monotone"
                      withDots={chartRows.length <= 36}
                      withLegend
                      gridAxis="xy"
                      strokeWidth={2}
                      tickLine="xy"
                      valueFormatter={(value) => value.toFixed(2)}
                      xAxisProps={{ interval: Math.max(0, Math.floor(chartRows.length / 6)) }}
                    />
                  </Box>
                ) : null}
                {result && chartRows.length === 0 ? (
                  <Text>Esta consulta no devolvió puntos.</Text>
                ) : null}
                <div>
                  <Text className="eyebrow">Estadística</Text>
                  {result ? (
                    <Table withRowBorders={false} verticalSpacing="xs" mt="xs">
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>Variable</Table.Th>
                          <Table.Th>Por década</Table.Th>
                          <Table.Th>p</Table.Th>
                          <Table.Th>Resultado</Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {result.statistics.map((stat) => (
                          <Table.Tr key={stat.variable}>
                            <Table.Td>{names.get(stat.variable) ?? stat.variable}</Table.Td>
                            <Table.Td ff="monospace">
                              {stat.slope_per_decade > 0 ? "+" : ""}
                              {stat.slope_per_decade.toFixed(2)}
                            </Table.Td>
                            <Table.Td ff="monospace">{formatP(stat.p_value)}</Table.Td>
                            <Table.Td>
                              {stat.n < 8
                                ? "Intervalo corto"
                                : stat.significant
                                  ? "Significativa"
                                  : "No significativa"}
                            </Table.Td>
                          </Table.Tr>
                        ))}
                      </Table.Tbody>
                    </Table>
                  ) : (
                    <Text size="sm" mt="xs">
                      Mann-Kendall y la pendiente de Theil-Sen aparecen aquí.
                    </Text>
                  )}
                  {result ? (
                    <Text size="xs" mt={6}>
                      Prueba de Mann-Kendall sobre la anomalía. n = {result.statistics[0]?.n ?? 0}.
                    </Text>
                  ) : null}
                </div>
                <Box id="conclusion" className="conclusion">
                  <Text className="eyebrow">Conclusión</Text>
                  <Text className="finding" mt="xs">
                    {result?.conclusion ??
                      "La conclusión va a decir el orden en el tiempo, no una causa."}
                  </Text>
                  <Text size="sm" mt="sm">
                    {result?.caveat ??
                      "Una sucesión temporal no demuestra causalidad."}
                  </Text>
                </Box>
              </Stack>
            </Paper>
          </Grid.Col>
        </Grid>
      </AppShell.Main>
    </AppShell>
  );
}

function LegendSwatch({ tone, label }: { tone: "high" | "low" | "hot" | "place"; label: string }) {
  return (
    <Group gap={6}>
      <span className={`swatch swatch-${tone}`} />
      <Text size="xs">{label}</Text>
    </Group>
  );
}

function formatP(value: number): string {
  if (!Number.isFinite(value)) return "n/d";
  if (value < 0.001) return "< 0.001";
  return value.toFixed(3);
}
