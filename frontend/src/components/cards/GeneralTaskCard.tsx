import Link from "next/link";
import type { Task } from "@/services/api";
import StatusBadge from "@/components/StatusBadge";
import { GitHubIcon, TasksIcon } from "@/components/icons/ServiceIcons";

const TYPE_LABELS: Record<string, { label: string; style: string }> = {
  coding_task: { label: "Coding", style: "text-indigo-600 bg-indigo-50" },
  spec_generation: { label: "Spec", style: "text-amber-600 bg-amber-50" },
  general: { label: "General", style: "text-gray-600 bg-gray-100" },
};

const SOURCE_ICONS: Record<string, React.FC<{ className?: string }>> = {
  github: GitHubIcon,
  frontend: TasksIcon,
  scheduler: TasksIcon,
};

const PRIORITY_COLORS: Record<string, string> = {
  critical: "text-red-600 bg-red-50",
  high: "text-orange-600 bg-orange-50",
  medium: "text-blue-600 bg-blue-50",
  low: "text-gray-600 bg-gray-50",
};

export default function GeneralTaskCard({ task }: { task: Task }) {
  const typeInfo = TYPE_LABELS[task.type] || TYPE_LABELS.general;
  const SourceIcon = SOURCE_ICONS[task.source] || TasksIcon;
  const hasResult = !!task.result;

  return (
    <Link href={`/tasks/${task.task_id}`}>
      <div className="bg-white rounded-lg border-l-4 border-gray-400 shadow-sm hover:shadow-md transition-shadow p-4 cursor-pointer">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <SourceIcon className="w-5 h-5 text-gray-500 flex-shrink-0" />
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${typeInfo.style}`}>
                  {typeInfo.label}
                </span>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PRIORITY_COLORS[task.priority] || PRIORITY_COLORS.medium}`}>
                  {task.priority}
                </span>
                {hasResult && (
                  <span className="text-xs px-2 py-0.5 rounded-full font-medium text-green-600 bg-green-50">
                    Has output
                  </span>
                )}
              </div>
            </div>
          </div>
          <StatusBadge status={task.status} />
        </div>
        <p className="mt-2 text-sm text-gray-700 line-clamp-2">
          {task.instruction_preview || task.instruction}
        </p>
        <div className="mt-2 flex items-center justify-between text-xs text-gray-400">
          <div className="flex items-center gap-2">
            <span>{task.task_id}</span>
            <span className="text-gray-300">|</span>
            <span>{task.source}</span>
          </div>
          <span>{new Date(task.created_at).toLocaleString()}</span>
        </div>
      </div>
    </Link>
  );
}
