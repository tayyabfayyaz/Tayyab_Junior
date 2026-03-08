import Link from "next/link";
import type { Task } from "@/services/api";
import StatusBadge from "@/components/StatusBadge";
import { EmailIcon } from "@/components/icons/ServiceIcons";

function parseEmailContext(context: string) {
  const lines = context.split("\n");
  let from = "";
  let subject = "";
  let body = "";
  let pastHeaders = false;

  for (const line of lines) {
    if (line.startsWith("From:")) from = line.replace("From:", "").trim();
    else if (line.startsWith("Subject:")) subject = line.replace("Subject:", "").trim();
    else if (pastHeaders || (!line.includes(":") && line.trim())) {
      pastHeaders = true;
      body += line + "\n";
    }
  }
  return { from: from || "Unknown sender", subject: subject || "No subject", body: body.trim() };
}

const PRIORITY_COLORS: Record<string, string> = {
  critical: "text-red-600 bg-red-50",
  high: "text-orange-600 bg-orange-50",
  medium: "text-blue-600 bg-blue-50",
  low: "text-gray-600 bg-gray-50",
};

export default function EmailTaskCard({ task }: { task: Task }) {
  const { from, subject, body } = parseEmailContext(task.context || task.instruction);
  const typeLabel = task.type === "email_draft" ? "Draft" : "Reply";

  return (
    <Link href={`/tasks/${task.task_id}`}>
      <div className="bg-white rounded-lg border-l-4 border-blue-400 shadow-sm hover:shadow-md transition-shadow p-4 cursor-pointer">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <EmailIcon className="w-5 h-5 text-blue-500 flex-shrink-0" />
            <div className="min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{from}</p>
              <p className="text-sm text-gray-700 truncate">{subject}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PRIORITY_COLORS[task.priority] || PRIORITY_COLORS.medium}`}>
              {typeLabel}
            </span>
            <StatusBadge status={task.status} />
          </div>
        </div>
        {body && (
          <p className="mt-2 text-xs text-gray-500 line-clamp-2">{body}</p>
        )}
        <div className="mt-2 flex items-center justify-between text-xs text-gray-400">
          <span>{task.task_id}</span>
          <span>{new Date(task.created_at).toLocaleString()}</span>
        </div>
      </div>
    </Link>
  );
}
