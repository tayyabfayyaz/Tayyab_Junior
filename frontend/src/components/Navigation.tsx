"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, useCallback } from "react";
import { SERVICES } from "@/lib/serviceConfig";
import { ServiceIcon, DashboardIcon } from "@/components/icons/ServiceIcons";
import ServiceStatusIndicator from "@/components/ServiceStatusIndicator";
import TabBadge from "@/components/TabBadge";
import { getHealth, listTasks } from "@/services/api";

export default function Navigation() {
  const pathname = usePathname();
  const [healthMap, setHealthMap] = useState<Record<string, string>>({});
  const [countMap, setCountMap] = useState<Record<string, number>>({});

  const fetchNavData = useCallback(async () => {
    try {
      const [health, tasks] = await Promise.all([
        getHealth().catch(() => null),
        listTasks({ status: "need_action", limit: 1 }).catch(() => null),
      ]);
      if (health?.services?.watchers) {
        setHealthMap(health.services.watchers);
      }
      // Fetch pending counts per service source
      const counts: Record<string, number> = {};
      await Promise.all(
        SERVICES.map(async (svc) => {
          try {
            const results = await Promise.all(
              svc.taskSources.map((src) =>
                listTasks({ source: src, status: "need_action", limit: 1 })
              )
            );
            counts[svc.id] = results.reduce((sum, r) => sum + r.total, 0);
          } catch {
            counts[svc.id] = 0;
          }
        })
      );
      setCountMap(counts);
    } catch {}
  }, []);

  useEffect(() => {
    fetchNavData();
    const interval = setInterval(fetchNavData, 15000);
    return () => clearInterval(interval);
  }, [fetchNavData]);

  const getWatcherStatus = (key: string): "active" | "inactive" | "unknown" => {
    const val = healthMap[key];
    if (!val) return "unknown";
    return val === "active" || val === "running" ? "active" : "inactive";
  };

  return (
    <aside className="w-60 bg-gray-900 text-gray-100 min-h-screen flex flex-col">
      {/* Brand */}
      <div className="p-5 border-b border-gray-700">
        <h1 className="text-xl font-bold tracking-tight">FTE</h1>
        <p className="text-xs text-gray-400 mt-0.5">Fully Task Executor</p>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {/* Dashboard */}
        <Link
          href="/"
          className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
            pathname === "/"
              ? "bg-gray-700 text-white font-medium"
              : "text-gray-300 hover:bg-gray-800 hover:text-white"
          }`}
        >
          <DashboardIcon className="w-5 h-5" />
          <span>Dashboard</span>
        </Link>

        {/* Divider */}
        <div className="pt-3 pb-2">
          <p className="px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Services</p>
        </div>

        {/* Service Tabs */}
        {SERVICES.map((svc) => {
          const isActive = pathname.startsWith(svc.href);
          const status = getWatcherStatus(svc.healthKey);
          const pendingCount = countMap[svc.id] || 0;

          return (
            <Link
              key={svc.id}
              href={svc.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive
                  ? "bg-gray-700 text-white font-medium"
                  : "text-gray-300 hover:bg-gray-800 hover:text-white"
              }`}
            >
              <ServiceIcon name={svc.icon} className={`w-5 h-5 ${isActive ? svc.accentText : ""}`} />
              <span className="flex-1">{svc.label}</span>
              <div className="flex items-center gap-2">
                <ServiceStatusIndicator status={status} />
                <TabBadge count={pendingCount} color={isActive ? `${svc.accentBg} ${svc.accentText}` : "bg-gray-700 text-gray-300"} />
              </div>
            </Link>
          );
        })}

        {/* Divider */}
        <div className="pt-3 pb-2">
          <p className="px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Other</p>
        </div>

        {/* All Tasks link */}
        <Link
          href="/tasks"
          className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
            pathname === "/tasks"
              ? "bg-gray-700 text-white font-medium"
              : "text-gray-300 hover:bg-gray-800 hover:text-white"
          }`}
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 6.75h12M8.25 12h12m-12 5.25h12M3.75 6.75h.007v.008H3.75V6.75zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zM3.75 12h.007v.008H3.75V12zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm-.375 5.25h.007v.008H3.75v-.008zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
          </svg>
          <span>All Tasks</span>
        </Link>

        {/* Reports link */}
        <Link
          href="/reports"
          className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
            pathname.startsWith("/reports")
              ? "bg-gray-700 text-white font-medium"
              : "text-gray-300 hover:bg-gray-800 hover:text-white"
          }`}
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
          <span>Reports</span>
        </Link>

        {/* Finance link */}
        <Link
          href="/finance"
          className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
            pathname.startsWith("/finance")
              ? "bg-gray-700 text-white font-medium"
              : "text-gray-300 hover:bg-gray-800 hover:text-white"
          }`}
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>Finance</span>
        </Link>
      </nav>

      <div className="p-4 border-t border-gray-700 text-xs text-gray-500">
        v1.0.0
      </div>
    </aside>
  );
}
