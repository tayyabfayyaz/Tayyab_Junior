"use client";

import { useState } from "react";
import { createManualTask } from "@/services/api";

interface TaskFormProps {
  onCreated: () => void;
  defaultType?: string;
  allowedTypes?: string[];
  serviceLabel?: string;
}

const ALL_TYPES = ["general", "email_reply", "email_draft", "social_post", "social_reply", "whatsapp_reply", "coding_task", "spec_generation"];
const PRIORITIES = ["medium", "critical", "high", "low"];

export default function TaskForm({ onCreated, defaultType, allowedTypes, serviceLabel }: TaskFormProps) {
  const types = allowedTypes || ALL_TYPES;
  const [type, setType] = useState(defaultType || types[0]);
  const [priority, setPriority] = useState("medium");
  const [instruction, setInstruction] = useState("");
  const [context, setContext] = useState("");
  const [constraints, setConstraints] = useState("");
  const [expectedOutput, setExpectedOutput] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!instruction.trim()) {
      setError("Instruction is required");
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      await createManualTask({
        type,
        priority,
        instruction,
        context,
        constraints: constraints || undefined,
        expected_output: expectedOutput || undefined,
      });
      setInstruction("");
      setContext("");
      setConstraints("");
      setExpectedOutput("");
      onCreated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create task");
    }
    setSubmitting(false);
  };

  const title = serviceLabel ? `Create New ${serviceLabel} Task` : "Create New Task";

  return (
    <form onSubmit={handleSubmit} className="bg-white border rounded-lg p-6 space-y-4">
      <h2 className="text-lg font-semibold">{title}</h2>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded p-2 text-sm text-red-700">{error}</div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
          <select value={type} onChange={(e) => setType(e.target.value)} className="w-full border rounded px-3 py-2 text-sm">
            {types.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
          <select value={priority} onChange={(e) => setPriority(e.target.value)} className="w-full border rounded px-3 py-2 text-sm">
            {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Instruction *</label>
        <textarea
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          rows={3}
          className="w-full border rounded px-3 py-2 text-sm"
          placeholder="What should the AI assistant do?"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Context</label>
        <textarea
          value={context}
          onChange={(e) => setContext(e.target.value)}
          rows={2}
          className="w-full border rounded px-3 py-2 text-sm"
          placeholder="Background information for this task"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Constraints</label>
        <textarea
          value={constraints}
          onChange={(e) => setConstraints(e.target.value)}
          rows={2}
          className="w-full border rounded px-3 py-2 text-sm"
          placeholder="Any restrictions (tone, format, length)"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Expected Output</label>
        <textarea
          value={expectedOutput}
          onChange={(e) => setExpectedOutput(e.target.value)}
          rows={2}
          className="w-full border rounded px-3 py-2 text-sm"
          placeholder="What format should the output be in?"
        />
      </div>

      <button
        type="submit"
        disabled={submitting}
        className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50 text-sm"
      >
        {submitting ? "Creating..." : "Create Task"}
      </button>
    </form>
  );
}
