import Link from "next/link";
import type { Task } from "@/services/api";
import StatusBadge from "@/components/StatusBadge";

function parseWhatsAppContext(context: string) {
  const lines = context.split("\n");
  let from = "";
  let message = "";
  let pastHeaders = false;

  for (const line of lines) {
    if (line.startsWith("From:") || line.startsWith("Phone:")) from = line.split(":").slice(1).join(":").trim();
    else if (pastHeaders || (!line.includes(":") && line.trim())) {
      pastHeaders = true;
      message += line + "\n";
    }
  }
  return { from: from || "Unknown contact", message: message.trim() || context };
}

const STATUS_ICONS: Record<string, string> = {
  need_action: "text-yellow-500",
  processing: "text-blue-500",
  done: "text-green-500",
  failed: "text-red-500",
};

export default function WhatsAppTaskCard({ task }: { task: Task }) {
  const { from, message } = parseWhatsAppContext(task.context || task.instruction);

  return (
    <Link href={`/tasks/${task.task_id}`}>
      <div className="bg-white rounded-lg border-l-4 border-green-400 shadow-sm hover:shadow-md transition-shadow p-4 cursor-pointer">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0">
              <span className="text-green-700 text-sm font-bold">
                {from.charAt(0).toUpperCase()}
              </span>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">{from}</p>
              <p className="text-xs text-gray-500">WhatsApp</p>
            </div>
          </div>
          <StatusBadge status={task.status} />
        </div>
        <div className="mt-3 bg-green-50 rounded-lg p-3">
          <p className="text-sm text-gray-800 line-clamp-3">{message}</p>
        </div>
        <div className="mt-2 flex items-center justify-between text-xs text-gray-400">
          <span>{task.task_id}</span>
          <span className={STATUS_ICONS[task.status] || ""}>
            {new Date(task.created_at).toLocaleString()}
          </span>
        </div>
      </div>
    </Link>
  );
}
