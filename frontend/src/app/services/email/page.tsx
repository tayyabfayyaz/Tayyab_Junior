"use client";

import ServiceLayout from "@/components/ServiceLayout";
import EmailTaskCard from "@/components/cards/EmailTaskCard";
import type { Task } from "@/services/api";

export default function EmailServicePage() {
  return (
    <ServiceLayout
      serviceId="email"
      renderCard={(task: Task) => <EmailTaskCard task={task} />}
    />
  );
}
