/**
 * T041: Task detail page — full task view with retry button, auto-refresh.
 */

"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import StatusBadge from "@/components/StatusBadge";
import { ServiceIcon } from "@/components/icons/ServiceIcons";
import { getServiceForTask } from "@/lib/serviceConfig";
import { getTask, retryTask, approveTask, rejectTask, Task } from "@/services/api";

export default function TaskDetailPage() {
  const params = useParams();
  const router = useRouter();
  const taskId = params.id as string;

  const [task, setTask] = useState<Task | null>(null);
  const [error, setError] = useState("");
  const [retrying, setRetrying] = useState(false);
  const [approving, setApproving] = useState(false);
  const [rejecting, setRejecting] = useState(false);

  const fetchTask = async () => {
    try {
      const data = await getTask(taskId);
      setTask(data);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load task");
    }
  };

  useEffect(() => {
    fetchTask();
    const interval = setInterval(fetchTask, 5000);
    return () => clearInterval(interval);
  }, [taskId]);

  const handleRetry = async () => {
    setRetrying(true);
    try {
      await retryTask(taskId);
      await fetchTask();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Retry failed");
    }
    setRetrying(false);
  };

  const handleApprove = async () => {
    setApproving(true);
    try {
      await approveTask(taskId);
      await fetchTask();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approval failed");
    }
    setApproving(false);
  };

  const handleReject = async () => {
    setRejecting(true);
    try {
      await rejectTask(taskId);
      await fetchTask();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Rejection failed");
    }
    setRejecting(false);
  };

  if (error && !task) {
    return (
      <div className="bg-red-50 border border-red-200 rounded p-4 text-red-700">
        {error}
      </div>
    );
  }

  if (!task) {
    return <div className="text-gray-500">Loading...</div>;
  }

  return (
    <div className="max-w-3xl">
      {(() => {
        const svc = getServiceForTask(task.type, task.source);
        return svc ? (
          <Link href={svc.href} className="inline-flex items-center gap-1.5 text-sm text-blue-600 hover:underline mb-4">
            <ServiceIcon name={svc.icon} className={`w-4 h-4 ${svc.accentText}`} />
            Back to {svc.label}
          </Link>
        ) : (
          <button onClick={() => router.back()} className="text-sm text-blue-600 hover:underline mb-4">
            Back
          </button>
        );
      })()}

      <div className="bg-white border rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-xl font-bold font-mono">{task.task_id}</h1>
          <StatusBadge status={task.status} />
        </div>

        <div className="grid grid-cols-3 gap-4 mb-6 text-sm">
          <div>
            <span className="text-gray-500">Type</span>
            <p className="font-medium">{task.type}</p>
          </div>
          <div>
            <span className="text-gray-500">Priority</span>
            <p className="font-medium">{task.priority}</p>
          </div>
          <div>
            <span className="text-gray-500">Source</span>
            <p className="font-medium">{task.source}</p>
          </div>
          <div>
            <span className="text-gray-500">Created</span>
            <p>{new Date(task.created_at).toLocaleString()}</p>
          </div>
          <div>
            <span className="text-gray-500">Updated</span>
            <p>{new Date(task.updated_at).toLocaleString()}</p>
          </div>
          <div>
            <span className="text-gray-500">Retries</span>
            <p>{task.retry_count}</p>
          </div>
        </div>

        {task.source_ref && (
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-gray-600 mb-1">Source Reference</h3>
            <p className="text-sm text-gray-700 font-mono">{task.source_ref}</p>
          </div>
        )}

        <div className="space-y-4">
          <Section title="Context" content={task.context} />
          <Section title="Instruction" content={task.instruction} />
          {task.constraints && <Section title="Constraints" content={task.constraints} />}
          {task.expected_output && <Section title="Expected Output" content={task.expected_output} />}
          {task.result && <Section title="Result" content={task.result} highlight="green" />}
          {task.error && <Section title="Error" content={task.error} highlight="red" />}
        </div>

        {task.status === "awaiting_approval" && (
          <div className="mt-6 flex gap-3">
            <button
              onClick={handleApprove}
              disabled={approving || rejecting}
              className="bg-green-600 text-white px-5 py-2 rounded hover:bg-green-700 disabled:opacity-50 text-sm font-medium"
            >
              {approving ? "Approving..." : "Approve"}
            </button>
            <button
              onClick={handleReject}
              disabled={approving || rejecting}
              className="bg-red-600 text-white px-5 py-2 rounded hover:bg-red-700 disabled:opacity-50 text-sm font-medium"
            >
              {rejecting ? "Rejecting..." : "Reject"}
            </button>
          </div>
        )}

        {task.status === "failed" && (
          <button
            onClick={handleRetry}
            disabled={retrying}
            className="mt-6 bg-orange-500 text-white px-4 py-2 rounded hover:bg-orange-600 disabled:opacity-50 text-sm"
          >
            {retrying ? "Retrying..." : "Retry Task"}
          </button>
        )}
      </div>
    </div>
  );
}

function Section({ title, content, highlight }: { title: string; content: string; highlight?: string }) {
  const bgClass = highlight === "green" ? "bg-green-50 border-green-200" : highlight === "red" ? "bg-red-50 border-red-200" : "bg-gray-50 border-gray-200";
  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-600 mb-1">{title}</h3>
      <div className={`border rounded p-3 text-sm whitespace-pre-wrap ${bgClass}`}>{content}</div>
    </div>
  );
}
