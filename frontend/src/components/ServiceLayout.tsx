"use client";

import { useState } from "react";
import type { Task } from "@/services/api";
import { getServiceById, type ServiceConfig } from "@/lib/serviceConfig";
import { useServiceTasks } from "@/hooks/useServiceTasks";
import { useServiceHealth } from "@/hooks/useServiceHealth";
import { ServiceIcon } from "@/components/icons/ServiceIcons";
import ServiceStatusIndicator from "@/components/ServiceStatusIndicator";
import TaskForm from "@/components/TaskForm";

interface SubFilter {
  key: string;
  label: string;
  options: { value: string; label: string }[];
}

interface ServiceLayoutProps {
  serviceId: string;
  renderCard: (task: Task) => React.ReactNode;
  subFilters?: SubFilter[];
}

const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "need_action", label: "Pending" },
  { value: "processing", label: "Processing" },
  { value: "done", label: "Completed" },
  { value: "failed", label: "Failed" },
];

export default function ServiceLayout({ serviceId, renderCard, subFilters }: ServiceLayoutProps) {
  const service = getServiceById(serviceId);
  if (!service) return <div className="p-8 text-red-500">Unknown service: {serviceId}</div>;

  return <ServiceLayoutInner service={service} renderCard={renderCard} subFilters={subFilters} />;
}

function ServiceLayoutInner({
  service,
  renderCard,
  subFilters,
}: {
  service: ServiceConfig;
  renderCard: (task: Task) => React.ReactNode;
  subFilters?: SubFilter[];
}) {
  const [statusFilter, setStatusFilter] = useState("");
  const [subFilterValues, setSubFilterValues] = useState<Record<string, string>>({});
  const [showForm, setShowForm] = useState(false);

  const sourceOverride = subFilterValues["source"] || undefined;

  const { tasks, total, loading, error, refetch } = useServiceTasks(service, {
    status: statusFilter || undefined,
    source: sourceOverride,
  });

  const { getStatus } = useServiceHealth();
  const healthStatus = getStatus(service.healthKey);

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${service.accentBg}`}>
            <ServiceIcon name={service.icon} className={`w-6 h-6 ${service.accentText}`} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-gray-900">{service.label}</h1>
              <ServiceStatusIndicator status={healthStatus} />
            </div>
            <p className="text-sm text-gray-500">{service.description}</p>
          </div>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            showForm
              ? "bg-gray-200 text-gray-700 hover:bg-gray-300"
              : `${service.accentBg} ${service.accentText} hover:opacity-80`
          }`}
        >
          {showForm ? "Cancel" : "+ New Task"}
        </button>
      </div>

      {/* Task Form */}
      {showForm && (
        <div className="mb-6">
          <TaskForm
            onCreated={() => {
              setShowForm(false);
              refetch();
            }}
            allowedTypes={service.taskTypes}
            defaultType={service.taskTypes[0]}
            serviceLabel={service.label}
          />
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="border rounded-lg px-3 py-1.5 text-sm text-gray-700 bg-white"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>

        {subFilters?.map((sf) => (
          <select
            key={sf.key}
            value={subFilterValues[sf.key] || ""}
            onChange={(e) => setSubFilterValues((prev) => ({ ...prev, [sf.key]: e.target.value }))}
            className="border rounded-lg px-3 py-1.5 text-sm text-gray-700 bg-white"
          >
            <option value="">All {sf.label}</option>
            {sf.options.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        ))}

        <span className="ml-auto text-sm text-gray-500">
          {loading ? "Loading..." : `${total} task${total !== 1 ? "s" : ""}`}
        </span>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Task List */}
      <div className="space-y-3">
        {!loading && tasks.length === 0 && (
          <div className="text-center py-12 text-gray-400">
            <ServiceIcon name={service.icon} className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-lg">No {service.label.toLowerCase()} tasks yet</p>
            <p className="text-sm mt-1">Tasks will appear here when created or triggered by watchers</p>
          </div>
        )}
        {tasks.map((task) => (
          <div key={task.task_id}>{renderCard(task)}</div>
        ))}
      </div>
    </div>
  );
}
