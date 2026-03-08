interface ServiceStatusIndicatorProps {
  status: "active" | "inactive" | "unknown";
}

export default function ServiceStatusIndicator({ status }: ServiceStatusIndicatorProps) {
  const colors = {
    active: "bg-green-400",
    inactive: "bg-gray-400",
    unknown: "bg-yellow-400",
  };

  return (
    <span className="relative flex h-2 w-2">
      {status === "active" && (
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
      )}
      <span className={`relative inline-flex rounded-full h-2 w-2 ${colors[status]}`} />
    </span>
  );
}
