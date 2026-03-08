import Link from "next/link";
import type { Task } from "@/services/api";
import StatusBadge from "@/components/StatusBadge";
import { LinkedInIcon, TwitterIcon } from "@/components/icons/ServiceIcons";

const PRIORITY_COLORS: Record<string, string> = {
  critical: "text-red-600 bg-red-50",
  high: "text-orange-600 bg-orange-50",
  medium: "text-purple-600 bg-purple-50",
  low: "text-gray-600 bg-gray-50",
};

export default function SocialTaskCard({ task }: { task: Task }) {
  const isLinkedIn = task.source === "linkedin";
  const PlatformIcon = isLinkedIn ? LinkedInIcon : TwitterIcon;
  const platformLabel = isLinkedIn ? "LinkedIn" : "Twitter";
  const typeLabel = task.type === "social_post" ? "Post" : "Reply";
  const content = task.instruction || "";
  const charCount = content.length;

  return (
    <Link href={`/tasks/${task.task_id}`}>
      <div className="bg-white rounded-lg border-l-4 border-purple-400 shadow-sm hover:shadow-md transition-shadow p-4 cursor-pointer">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <PlatformIcon className="w-5 h-5 text-purple-500 flex-shrink-0" />
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-900">{platformLabel}</span>
                <span className="text-xs text-purple-600 bg-purple-50 px-2 py-0.5 rounded-full">{typeLabel}</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PRIORITY_COLORS[task.priority] || PRIORITY_COLORS.medium}`}>
              {task.priority}
            </span>
            <StatusBadge status={task.status} />
          </div>
        </div>
        <p className="mt-2 text-sm text-gray-700 line-clamp-3">{content}</p>
        <div className="mt-2 flex items-center justify-between text-xs text-gray-400">
          <div className="flex items-center gap-3">
            <span>{task.task_id}</span>
            {!isLinkedIn && <span className={charCount > 280 ? "text-red-500" : ""}>{charCount} chars</span>}
          </div>
          <span>{new Date(task.created_at).toLocaleString()}</span>
        </div>
      </div>
    </Link>
  );
}
