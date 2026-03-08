"use client";

import { useState, useEffect, useCallback } from "react";
import { getHealth } from "@/services/api";

interface ServiceHealthState {
  watchers: Record<string, string>;
  loading: boolean;
  error: string | null;
}

export function useServiceHealth(pollInterval = 30000) {
  const [state, setState] = useState<ServiceHealthState>({
    watchers: {},
    loading: true,
    error: null,
  });

  const fetchHealth = useCallback(async () => {
    try {
      const health = await getHealth();
      setState({
        watchers: health.services?.watchers || {},
        loading: false,
        error: null,
      });
    } catch (e) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: e instanceof Error ? e.message : "Failed to fetch health",
      }));
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, pollInterval);
    return () => clearInterval(interval);
  }, [fetchHealth, pollInterval]);

  const getStatus = useCallback(
    (healthKey: string): "active" | "inactive" | "unknown" => {
      if (state.loading) return "unknown";
      const val = state.watchers[healthKey];
      if (!val) return "unknown";
      return val === "active" || val === "running" ? "active" : "inactive";
    },
    [state.watchers, state.loading]
  );

  return { ...state, getStatus };
}
