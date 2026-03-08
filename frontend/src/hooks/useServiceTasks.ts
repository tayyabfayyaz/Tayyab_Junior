"use client";

import { useState, useEffect, useCallback } from "react";
import { listTasksByService, type Task } from "@/services/api";
import type { ServiceConfig } from "@/lib/serviceConfig";

interface UseServiceTasksOptions {
  status?: string;
  priority?: string;
  source?: string;
  limit?: number;
}

interface ServiceTasksState {
  tasks: Task[];
  total: number;
  loading: boolean;
  error: string | null;
}

export function useServiceTasks(
  service: ServiceConfig,
  options: UseServiceTasksOptions = {},
  pollInterval = 5000
) {
  const [state, setState] = useState<ServiceTasksState>({
    tasks: [],
    total: 0,
    loading: true,
    error: null,
  });

  const sources = options.source
    ? [options.source]
    : service.taskSources;

  const fetchTasks = useCallback(async () => {
    try {
      const result = await listTasksByService(sources, {
        status: options.status,
        priority: options.priority,
        limit: options.limit || 50,
      });
      setState({
        tasks: result.tasks,
        total: result.total,
        loading: false,
        error: null,
      });
    } catch (e) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: e instanceof Error ? e.message : "Failed to fetch tasks",
      }));
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [options.status, options.priority, options.source, options.limit, service.id]);

  useEffect(() => {
    setState((prev) => ({ ...prev, loading: true }));
    fetchTasks();
    const interval = setInterval(fetchTasks, pollInterval);
    return () => clearInterval(interval);
  }, [fetchTasks, pollInterval]);

  return { ...state, refetch: fetchTasks };
}
