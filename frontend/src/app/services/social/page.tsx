"use client";

import ServiceLayout from "@/components/ServiceLayout";
import SocialTaskCard from "@/components/cards/SocialTaskCard";
import type { Task } from "@/services/api";

const PLATFORM_FILTERS = [
  { value: "linkedin", label: "LinkedIn" },
  { value: "twitter", label: "Twitter" },
];

export default function SocialServicePage() {
  return (
    <ServiceLayout
      serviceId="social"
      renderCard={(task: Task) => <SocialTaskCard task={task} />}
      subFilters={[
        { key: "source", label: "Platforms", options: PLATFORM_FILTERS },
      ]}
    />
  );
}
