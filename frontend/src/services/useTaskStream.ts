/**
 * T067: useTaskStream hook — EventSource-based React hook for real-time task updates via SSE.
 */

"use client";

import { useEffect, useRef, useState, useCallback } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface TaskStreamEvent {
  counts: Record<string, number>;
  recent_tasks: {
    task_id: string;
    status: string;
    type: string;
    updated_at: string;
  }[];
}

export function useTaskStream() {
  const [lastEvent, setLastEvent] = useState<TaskStreamEvent | null>(null);
  const [connected, setConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const connect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const es = new EventSource(`${API_BASE}/tasks/stream`);
    eventSourceRef.current = es;

    es.onopen = () => setConnected(true);

    es.onmessage = (event) => {
      try {
        const data: TaskStreamEvent = JSON.parse(event.data);
        setLastEvent(data);
      } catch {
        // Ignore malformed events
      }
    };

    es.onerror = () => {
      setConnected(false);
      es.close();
      // Reconnect after 5 seconds
      setTimeout(connect, 5000);
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      eventSourceRef.current?.close();
    };
  }, [connect]);

  return { lastEvent, connected };
}
