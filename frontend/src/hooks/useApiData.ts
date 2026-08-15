import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../services/api";

interface FetchState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

/**
 * Runs `fetcher` on mount and whenever `deps` change, exposing
 * loading/error/data plus a manual `refetch`. Centralizes the
 * loading/error/empty-state handling every page needs against the
 * Phase 1 API.
 */
export function useApiData<T>(
  fetcher: () => Promise<T>,
  deps: React.DependencyList = [],
) {
  const [state, setState] = useState<FetchState<T>>({
    data: null,
    loading: true,
    error: null,
  });

  const load = useCallback(() => {
    let cancelled = false;
    setState((prev) => ({ ...prev, loading: true, error: null }));

    fetcher()
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null });
      })
      .catch((err) => {
        if (cancelled) return;
        const message =
          err instanceof ApiError ? err.message : "Something went wrong.";
        setState({ data: null, loading: false, error: message });
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    const cancel = load();
    return cancel;
  }, [load]);

  return { ...state, refetch: load };
}
