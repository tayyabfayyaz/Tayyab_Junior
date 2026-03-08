"use client";

import ServiceLayout from "@/components/ServiceLayout";
import GeneralTaskCard from "@/components/cards/GeneralTaskCard";
import type { Task } from "@/services/api";

export default function GeneralTasksServicePage() {
  return (
    <ServiceLayout
      serviceId="tasks"
      renderCard={(task: Task) => <GeneralTaskCard task={task} />}
    />
  );
}
