export interface ServiceConfig {
  id: string;
  label: string;
  href: string;
  icon: string;
  color: string;
  accentBg: string;
  accentBorder: string;
  accentText: string;
  taskTypes: string[];
  taskSources: string[];
  healthKey: string;
  description: string;
}

export const SERVICES: ServiceConfig[] = [
  {
    id: "email",
    label: "Email",
    href: "/services/email",
    icon: "email",
    color: "blue",
    accentBg: "bg-blue-50",
    accentBorder: "border-blue-400",
    accentText: "text-blue-600",
    taskTypes: ["email_reply", "email_draft"],
    taskSources: ["gmail"],
    healthKey: "email",
    description: "Gmail inbox monitoring and automated replies",
  },
  {
    id: "social",
    label: "Social",
    href: "/services/social",
    icon: "social",
    color: "purple",
    accentBg: "bg-purple-50",
    accentBorder: "border-purple-400",
    accentText: "text-purple-600",
    taskTypes: ["social_post", "social_reply"],
    taskSources: ["linkedin", "twitter"],
    healthKey: "social",
    description: "LinkedIn and Twitter content management",
  },
  {
    id: "whatsapp",
    label: "WhatsApp",
    href: "/services/whatsapp",
    icon: "whatsapp",
    color: "green",
    accentBg: "bg-green-50",
    accentBorder: "border-green-400",
    accentText: "text-green-600",
    taskTypes: ["whatsapp_reply"],
    taskSources: ["whatsapp"],
    healthKey: "whatsapp",
    description: "WhatsApp message handling and responses",
  },
  {
    id: "tasks",
    label: "Tasks",
    href: "/services/tasks",
    icon: "tasks",
    color: "gray",
    accentBg: "bg-gray-50",
    accentBorder: "border-gray-400",
    accentText: "text-gray-600",
    taskTypes: ["coding_task", "spec_generation", "general"],
    taskSources: ["github", "frontend", "scheduler"],
    healthKey: "github",
    description: "Coding, specs, and general automation tasks",
  },
];

export function getServiceById(id: string): ServiceConfig | undefined {
  return SERVICES.find((s) => s.id === id);
}

export function getServiceForTask(type: string, source: string): ServiceConfig | undefined {
  return SERVICES.find(
    (s) => s.taskTypes.includes(type) || s.taskSources.includes(source)
  );
}
