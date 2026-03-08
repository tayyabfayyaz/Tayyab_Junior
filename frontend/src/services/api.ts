/**
 * T034: Frontend API client — typed fetch wrapper for all backend endpoints.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface Task {
  task_id: string;
  type: string;
  priority: string;
  source: string;
  status: string;
  created_at: string;
  updated_at: string;
  retry_count: number;
  source_ref?: string;
  context: string;
  instruction: string;
  constraints?: string;
  expected_output?: string;
  result?: string;
  error?: string;
  instruction_preview?: string;
}

export interface TaskListResponse {
  tasks: Task[];
  total: number;
  limit: number;
  offset: number;
}

export interface TaskCreateData {
  type: string;
  priority: string;
  instruction: string;
  context: string;
  constraints?: string;
  expected_output?: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  services: {
    executor: string;
    watchers: Record<string, string>;
    mcp_server: string;
    task_dirs: Record<string, number>;
  };
}

export interface StatsResponse {
  period: string;
  total_tasks: number;
  by_status: Record<string, number>;
  by_type: Record<string, number>;
  avg_execution_time_ms: number;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

export async function listTasks(filters: {
  status?: string;
  type?: string;
  priority?: string;
  source?: string;
  limit?: number;
  offset?: number;
  sort?: string;
} = {}): Promise<TaskListResponse> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== "") params.set(k, String(v));
  });
  const qs = params.toString();
  return apiFetch<TaskListResponse>(`/tasks${qs ? `?${qs}` : ""}`);
}

export async function getTask(id: string): Promise<Task> {
  return apiFetch<Task>(`/tasks/${id}`);
}

export async function createManualTask(data: TaskCreateData): Promise<{ task_id: string; status: string; created_at: string }> {
  return apiFetch(`/tasks/manual`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function retryTask(id: string): Promise<{ task_id: string; status: string; retry_count: number }> {
  return apiFetch(`/tasks/${id}/retry`, { method: "POST" });
}

export async function approveTask(id: string): Promise<{ task_id: string; status: string }> {
  return apiFetch(`/tasks/${id}/approve`, { method: "POST" });
}

export async function rejectTask(id: string): Promise<{ task_id: string; status: string }> {
  return apiFetch(`/tasks/${id}/reject`, { method: "POST" });
}

export async function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}

export async function getStats(period: string = "all"): Promise<StatsResponse> {
  return apiFetch<StatsResponse>(`/stats?period=${period}`);
}

export interface ReportSummary {
  report_id: string;
  generated_at: string;
  title: string;
  total_tasks: number;
  completed: number;
  failed: number;
}

export interface ReportDetail extends ReportSummary {
  content: string;
}

export async function listReports(): Promise<ReportSummary[]> {
  return apiFetch<ReportSummary[]>("/reports");
}

export async function getReport(id: string): Promise<ReportDetail> {
  return apiFetch<ReportDetail>(`/reports/${id}`);
}

export async function triggerReport(): Promise<{ report_id: string; path: string }> {
  return apiFetch(`/reports/generate`, { method: "POST" });
}

export async function listTasksByService(
  sources: string[],
  filters: { status?: string; priority?: string; limit?: number; sort?: string } = {}
): Promise<{ tasks: Task[]; total: number }> {
  if (sources.length === 0) return { tasks: [], total: 0 };

  const results = await Promise.all(
    sources.map((source) =>
      listTasks({ ...filters, source, limit: filters.limit || 50, sort: filters.sort || "created_at:desc" })
    )
  );

  const allTasks = results.flatMap((r) => r.tasks);
  const total = results.reduce((sum, r) => sum + r.total, 0);

  allTasks.sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  return { tasks: allTasks, total };
}

// ── Finance ───────────────────────────────────────────────────────────────────

export interface Transaction {
  id: string;
  date: string;
  description: string;
  amount: number;
  currency: string;
  type: string;
  source: string;
  bank?: string;
  raw_ref?: string;
}

export interface TransactionsResponse {
  transactions: Transaction[];
  total: number;
  last_synced?: string;
}

export interface SyncResponse {
  synced: number;
  total: number;
  errors: string[];
}

export interface BusinessSummary {
  summary: string;
  generated_at: string;
  transaction_count: number;
  total_credits: number;
  total_debits: number;
  currency: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  reply: string;
  model: string;
}

export async function getTransactions(): Promise<TransactionsResponse> {
  return apiFetch<TransactionsResponse>("/finance/transactions");
}

export async function syncTransactions(): Promise<SyncResponse> {
  return apiFetch<SyncResponse>("/finance/transactions/sync", { method: "POST" });
}

export async function getBusinessSummary(): Promise<BusinessSummary> {
  return apiFetch<BusinessSummary>("/finance/business-summary");
}

export async function refreshBusinessSummary(): Promise<BusinessSummary> {
  return apiFetch<BusinessSummary>("/finance/business-summary/refresh", { method: "POST" });
}

export async function financeChat(messages: ChatMessage[]): Promise<ChatResponse> {
  return apiFetch<ChatResponse>("/finance/chat", {
    method: "POST",
    body: JSON.stringify({ messages }),
  });
}
