"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listTasks, getStats, getHealth, Task, StatsResponse, HealthResponse } from "@/services/api";
import { SERVICES } from "@/lib/serviceConfig";
import { ServiceIcon } from "@/components/icons/ServiceIcons";
import ServiceStatusIndicator from "@/components/ServiceStatusIndicator";
import StatusBadge from "@/components/StatusBadge";

const STATUS_CARDS = [
  { key: "need_action", label: "Pending", color: "border-yellow-400 bg-yellow-50", textColor: "text-yellow-700" },
  { key: "processing", label: "Processing", color: "border-blue-400 bg-blue-50", textColor: "text-blue-700" },
  { key: "done", label: "Completed", color: "border-green-400 bg-green-50", textColor: "text-green-700" },
  { key: "failed", label: "Failed", color: "border-red-400 bg-red-50", textColor: "text-red-700" },
];

export default function DashboardPage() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [recentTasks, setRecentTasks] = useState<Task[]>([]);
  const [serviceCounts, setServiceCounts] = useState<Record<string, number>>({});
  const [error, setError] = useState("");

  const fetchData = async () => {
    try {
      const [statsData, tasksData, healthData] = await Promise.all([
        getStats("today"),
        listTasks({ limit: 10, sort: "created_at:desc" }),
        getHealth().catch(() => null),
      ]);
      setStats(statsData);
      setRecentTasks(tasksData.tasks);
      if (healthData) setHealth(healthData);
      setError("");

      // Fetch per-service counts
      const counts: Record<string, number> = {};
      await Promise.all(
        SERVICES.map(async (svc) => {
          try {
            const results = await Promise.all(
              svc.taskSources.map((src) =>
                listTasks({ source: src, limit: 1 })
              )
            );
            counts[svc.id] = results.reduce((sum, r) => sum + r.total, 0);
          } catch {
            counts[svc.id] = 0;
          }
        })
      );
      setServiceCounts(counts);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load data");
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const getWatcherStatus = (key: string): "active" | "inactive" | "unknown" => {
    const val = health?.services?.watchers?.[key];
    if (!val) return "unknown";
    return val === "active" || val === "running" ? "active" : "inactive";
  };

  return (
    <div className="max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Status Stats */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {STATUS_CARDS.map((card) => (
          <div key={card.key} className={`border-l-4 rounded-lg p-4 ${card.color}`}>
            <p className="text-sm text-gray-600">{card.label}</p>
            <p className={`text-3xl font-bold mt-1 ${card.textColor}`}>
              {stats?.by_status?.[card.key] ?? 0}
            </p>
          </div>
        ))}
      </div>

      {/* Service Overview Cards */}
      <h2 className="text-lg font-semibold mb-3">Services</h2>
      <div className="grid grid-cols-2 gap-4 mb-8">
        {SERVICES.map((svc) => {
          const status = getWatcherStatus(svc.healthKey);
          const count = serviceCounts[svc.id] ?? 0;

          return (
            <Link key={svc.id} href={svc.href}>
              <div className={`border rounded-lg p-5 hover:shadow-md transition-shadow cursor-pointer border-l-4 ${svc.accentBorder}`}>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${svc.accentBg}`}>
                      <ServiceIcon name={svc.icon} className={`w-5 h-5 ${svc.accentText}`} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">{svc.label}</h3>
                      <p className="text-xs text-gray-500">{svc.description}</p>
                    </div>
                  </div>
                  <ServiceStatusIndicator status={status} />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">{count} task{count !== 1 ? "s" : ""}</span>
                  <span className={`text-xs font-medium ${svc.accentText}`}>View &rarr;</span>
                </div>
              </div>
            </Link>
          );
        })}
      </div>

      {/* Recent Tasks */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold">Recent Tasks</h2>
        <Link href="/tasks" className="text-sm text-blue-600 hover:text-blue-800">
          View all &rarr;
        </Link>
      </div>
      <div className="space-y-2">
        {recentTasks.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <p>No tasks yet. Create one from a service page.</p>
          </div>
        ) : (
          recentTasks.map((task) => (
            <Link key={task.task_id} href={`/tasks/${task.task_id}`}>
              <div className="bg-white border rounded-lg p-3 hover:shadow-sm transition-shadow flex items-center gap-3">
                <ServiceIcon
                  name={SERVICES.find((s) => s.taskSources.includes(task.source))?.icon || "tasks"}
                  className={`w-4 h-4 flex-shrink-0 ${SERVICES.find((s) => s.taskSources.includes(task.source))?.accentText || "text-gray-400"}`}
                />
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-gray-800 truncate">
                    {task.instruction_preview || task.instruction}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {task.task_id} &middot; {task.type.replace(/_/g, " ")} &middot; {task.source}
                  </p>
                </div>
                <StatusBadge status={task.status} />
              </div>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}
