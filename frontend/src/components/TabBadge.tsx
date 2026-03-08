interface TabBadgeProps {
  count: number;
  color?: string;
}

export default function TabBadge({ count, color = "bg-gray-600 text-white" }: TabBadgeProps) {
  if (count === 0) return null;

  return (
    <span className={`ml-auto inline-flex items-center justify-center px-1.5 py-0.5 text-xs font-medium rounded-full ${color}`}>
      {count > 99 ? "99+" : count}
    </span>
  );
}
