/**
 * T040: Task list page — filterable, sortable, paginated task list with auto-refresh.
 */

"use client";

import { useEffect, useState } from "react";
import TaskCard from "@/components/TaskCard";
import TaskForm from "@/components/TaskForm";
import { listTasks, Task } from "@/services/api";

const STATUSES = ["", "awaiting_approval", "need_action", "processing", "done", "failed"];
const TYPES = ["", "email_reply", "email_draft", "social_post", "social_reply", "whatsapp_reply", "coding_task", "general"];
const PRIORITIES = ["", "critical", "high", "medium", "low"];

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState({ status: "", type: "", priority: "", source: "" });
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");

  const fetchTasks = async () => {
    try {
      const data = await listTasks({ ...filters, limit: 50 });
      setTasks(data.tasks);
      setTotal(data.total);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load tasks");
    }
  };

  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 5000);
    return () => clearInterval(interval);
  }, [filters]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Tasks ({total})</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm"
        >
          {showForm ? "Cancel" : "+ New Task"}
        </button>
      </div>

      {showForm && (
        <div className="mb-6">
          <TaskForm
            onCreated={() => {
              setShowForm(false);
              fetchTasks();
            }}
          />
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded p-3 mb-4 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="flex gap-3 mb-4">
        <select
          value={filters.status}
          onChange={(e) => setFilters({ ...filters, status: e.target.value })}
          className="border rounded px-3 py-1.5 text-sm bg-white"
        >
          <option value="">All Statuses</option>
          {STATUSES.filter(Boolean).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select
          value={filters.type}
          onChange={(e) => setFilters({ ...filters, type: e.target.value })}
          className="border rounded px-3 py-1.5 text-sm bg-white"
        >
          <option value="">All Types</option>
          {TYPES.filter(Boolean).map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <select
          value={filters.priority}
          onChange={(e) => setFilters({ ...filters, priority: e.target.value })}
          className="border rounded px-3 py-1.5 text-sm bg-white"
        >
          <option value="">All Priorities</option>
          {PRIORITIES.filter(Boolean).map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
      </div>

      <div className="space-y-3">
        {tasks.length === 0 ? (
          <p className="text-gray-500 text-sm">No tasks match your filters.</p>
        ) : (
          tasks.map((task) => <TaskCard key={task.task_id} task={task} />)
        )}
      </div>
    </div>
  );
}
