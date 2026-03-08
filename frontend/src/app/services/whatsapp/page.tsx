"use client";

import ServiceLayout from "@/components/ServiceLayout";
import WhatsAppTaskCard from "@/components/cards/WhatsAppTaskCard";
import type { Task } from "@/services/api";

export default function WhatsAppServicePage() {
  return (
    <ServiceLayout
      serviceId="whatsapp"
      renderCard={(task: Task) => <WhatsAppTaskCard task={task} />}
    />
  );
}
