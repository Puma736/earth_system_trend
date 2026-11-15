"use client";

import { TextInput } from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { useEffect, useState } from "react";
import type { PlaceRef } from "@/lib/investigation/types";

interface GeocodeHit {
  id: string;
  name: string;
  label: string;
  lat: number;
  lon: number;
}

export function PlaceSearch({
  place,
  onPlace,
}: {
  place: PlaceRef | null;
  onPlace: (place: PlaceRef | null) => void;
}) {
  const [text, setText] = useState(place?.name ?? "");
  const [debounced] = useDebouncedValue(text, 600);
  const [results, setResults] = useState<GeocodeHit[]>([]);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    const query = debounced.trim();
    if (query.length < 3) {
      setResults([]);
      setNote(null);
      return;
    }
    if (place && query === place.name) {
      setResults([]);
      setNote(null);
      return;
    }

    const controller = new AbortController();
    setNote("Buscando lugar");
    fetch(`/api/geocode?q=${encodeURIComponent(query)}`, {
      signal: controller.signal,
      cache: "no-store",
    })
      .then(async (response) => {
        const payload = (await response.json()) as GeocodeHit[] | { error?: string };
        if (!response.ok || !Array.isArray(payload)) {
          const message =
            !Array.isArray(payload) && payload.error
              ? payload.error
              : "No se pudo consultar el lugar.";
          throw new Error(message);
        }
        setResults(payload);
        setNote(payload.length === 0 ? "No hay lugares con ese nombre." : null);
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setResults([]);
        setNote(error instanceof Error ? error.message : "No se pudo consultar el lugar.");
      });

    return () => controller.abort();
  }, [debounced, place]);

  function choose(hit: GeocodeHit) {
    const next = { name: hit.name, lat: hit.lat, lon: hit.lon };
    setText(hit.name);
    setResults([]);
    setNote(null);
    onPlace(next);
  }

  return (
    <div>
      <TextInput
        id="place-search"
        label="Buscar lugar"
        placeholder="Ciudad, pueblo o lugar"
        size="sm"
        value={text}
        onChange={(event) => setText(event.currentTarget.value)}
        description={
          place
            ? `Área de análisis: ${place.name} (${place.lat.toFixed(2)}, ${place.lon.toFixed(2)})`
            : "Escribe y elige un resultado. La búsqueda espera a que termines de escribir."
        }
      />
      {place ? (
        <button
          type="button"
          className="text-button"
          onClick={() => {
            setText("");
            setResults([]);
            setNote(null);
            onPlace(null);
          }}
        >
          Quitar lugar
        </button>
      ) : null}
      {note ? (
        <p className="search-note" role="status">
          {note}
        </p>
      ) : null}
      {results.length > 0 ? (
        <div className="place-results" role="listbox" aria-label="Lugares">
          {results.map((hit) => (
            <button
              key={hit.id}
              type="button"
              className="place-hit"
              role="option"
              onMouseDown={(event) => {
                event.preventDefault();
                choose(hit);
              }}
            >
              {hit.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
