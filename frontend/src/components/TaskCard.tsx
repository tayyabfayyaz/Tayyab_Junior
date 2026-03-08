/**
 * T036: TaskCard component — display task summary.
 */

import Link from "next/link";
import StatusBadge from "./StatusBadge";
import { Task } from "@/services/api";

interface TaskCardProps {
  task: Task;
}

const PRIORITY_COLORS: Record<string, string> = {
  critical: "text-red-600",
  high: "text-orange-600",
  medium: "text-blue-600",
  low: "text-gray-500",
};

export default function TaskCard({ task }: TaskCardProps) {
  return (
    <Link href={`/tasks/${task.task_id}`}>
      <div className="border rounded-lg p-4 hover:shadow-md transition-shadow bg-white cursor-pointer">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-mono text-gray-500">{task.task_id}</span>
          <StatusBadge status={task.status} />
        </div>
        <p className="text-sm text-gray-800 mb-2 line-clamp-2">
          {task.instruction_preview || task.instruction}
        </p>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span className="bg-gray-100 px-2 py-0.5 rounded">{task.type}</span>
          <span className={`font-medium ${PRIORITY_COLORS[task.priority] || ""}`}>
            {task.priority}
          </span>
          <span>{task.source}</span>
          <span className="ml-auto">
            {new Date(task.created_at).toLocaleString()}
          </span>
        </div>
      </div>
    </Link>
  );
}
