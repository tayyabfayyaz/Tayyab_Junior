/**
 * T035: StatusBadge component — color-coded badge for task status.
 */

interface StatusBadgeProps {
  status: string;
}

const STATUS_STYLES: Record<string, string> = {
  awaiting_approval: "bg-purple-100 text-purple-800 border-purple-300",
  need_action: "bg-yellow-100 text-yellow-800 border-yellow-300",
  processing: "bg-blue-100 text-blue-800 border-blue-300",
  done: "bg-green-100 text-green-800 border-green-300",
  failed: "bg-red-100 text-red-800 border-red-300",
};

const STATUS_LABELS: Record<string, string> = {
  awaiting_approval: "Awaiting Approval",
  need_action: "Pending",
  processing: "Processing",
  done: "Completed",
  failed: "Failed",
};

export default function StatusBadge({ status }: StatusBadgeProps) {
  const style = STATUS_STYLES[status] || "bg-gray-100 text-gray-800 border-gray-300";
  const label = STATUS_LABELS[status] || status;

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${style}`}>
      {label}
    </span>
  );
}
