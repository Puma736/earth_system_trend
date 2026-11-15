"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, isAbortError } from "./api";

export type ResourceState<T> =
  | { status: "idle"; data: null; error: null }
  | { status: "loading"; data: T | null; error: null }
  | { status: "ready"; data: T; error: null }
  | { status: "error"; data: null; error: ApiError };

export type Resource<T> = ResourceState<T> & { retry: () => void };

const IDLE = { status: "idle", data: null, error: null } as const;

/**
 * Pide un recurso cada vez que cambia `key`; con `key` null no pide nada.
 * Mientras recarga conserva el dato anterior (la gráfica no parpadea) y cancela
 * la petición anterior si la clave cambia antes de que llegue la respuesta.
 */
export function useResource<T>(key: string | null, load: (signal: AbortSignal) => Promise<T>): Resource<T> {
  const loadRef = useRef(load);
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<ResourceState<T>>(IDLE);

  useEffect(() => {
    loadRef.current = load;
  });

  useEffect(() => {
    if (key === null) {
      setState(IDLE);
      return;
    }
    const controller = new AbortController();
    setState((previous) => ({ status: "loading", data: previous.data, error: null }));
    loadRef.current(controller.signal).then(
      (data) => {
        if (!controller.signal.aborted) setState({ status: "ready", data, error: null });
      },
      (reason: unknown) => {
        if (controller.signal.aborted || isAbortError(reason)) return;
        const error =
          reason instanceof ApiError
            ? reason
            : new ApiError(reason instanceof Error ? reason.message : "Unexpected error.", "network");
        setState({ status: "error", data: null, error });
      },
    );
    return () => controller.abort();
  }, [key, attempt]);

  const retry = useCallback(() => setAttempt((count) => count + 1), []);
  return { ...state, retry };
}
