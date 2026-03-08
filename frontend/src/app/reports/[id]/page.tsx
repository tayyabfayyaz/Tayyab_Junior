/**
 * Report detail page — renders full markdown content of a single CEO report.
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getReport, ReportDetail } from "@/services/api";

export default function ReportDetailPage({ params }: { params: { id: string } }) {
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getReport(params.id)
      .then(setReport)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load report"))
      .finally(() => setLoading(false));
  }, [params.id]);

  if (loading) {
    return <p className="text-gray-500 text-sm">Loading report...</p>;
  }

  if (error) {
    return (
      <div>
        <Link href="/reports" className="text-sm text-indigo-600 hover:underline mb-4 inline-block">
          ← Back to Reports
        </Link>
        <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>
      </div>
    );
  }

  if (!report) return null;

  // Strip YAML frontmatter for display
  const bodyContent = report.content.replace(/^---[\s\S]*?---\n/, "").trim();

  // Convert simple markdown to displayable HTML-safe text with basic formatting
  const renderMarkdown = (md: string) => {
    return md
      .split("\n")
      .map((line, i) => {
        if (line.startsWith("# ")) {
          return <h1 key={i} className="text-2xl font-bold mt-6 mb-2 text-gray-900">{line.slice(2)}</h1>;
        }
        if (line.startsWith("## ")) {
          return <h2 key={i} className="text-lg font-semibold mt-5 mb-2 text-gray-800 border-b border-gray-200 pb-1">{line.slice(3)}</h2>;
        }
        if (line.startsWith("### ")) {
          return <h3 key={i} className="text-base font-semibold mt-4 mb-1 text-gray-700">{line.slice(4)}</h3>;
        }
        if (line.startsWith("| ")) {
          // Table row
          const cells = line.split("|").filter((c) => c.trim() !== "");
          const isHeader = cells.every((c) => c.trim() !== "");
          if (line.match(/^\|[-| ]+\|$/)) {
            return null; // separator row
          }
          return (
            <tr key={i} className="border-b border-gray-100">
              {cells.map((cell, j) => (
                <td key={j} className="px-3 py-1.5 text-sm text-gray-700">{cell.trim()}</td>
              ))}
            </tr>
          );
        }
        if (line.startsWith("- ")) {
          const text = line.slice(2);
          return (
            <li key={i} className="text-sm text-gray-700 ml-4 list-disc" dangerouslySetInnerHTML={{ __html: text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>').replace(/`([^`]+)`/g, '<code class="bg-gray-100 px-1 rounded text-xs">$1</code>') }} />
          );
        }
        if (line === "") {
          return <div key={i} className="h-2" />;
        }
        return (
          <p key={i} className="text-sm text-gray-700" dangerouslySetInnerHTML={{ __html: line.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>').replace(/`([^`]+)`/g, '<code class="bg-gray-100 px-1 rounded text-xs">$1</code>') }} />
        );
      })
      .filter(Boolean);
  };

  // Wrap table rows in a proper table element
  const lines = bodyContent.split("\n");
  const elements: React.ReactNode[] = [];
  let tableRows: React.ReactNode[] = [];
  let inTable = false;
  let tableKey = 0;

  lines.forEach((line, i) => {
    if (line.startsWith("| ")) {
      if (line.match(/^\|[-| ]+\|$/)) return; // separator
      const cells = line.split("|").filter((c) => c.trim() !== "");
      if (!inTable) {
        inTable = true;
        // First row is header
        tableRows.push(
          <thead key="thead">
            <tr className="bg-gray-50">
              {cells.map((cell, j) => (
                <th key={j} className="px-3 py-2 text-xs font-semibold text-gray-600 text-left">{cell.trim()}</th>
              ))}
            </tr>
          </thead>
        );
      } else {
        tableRows.push(
          <tr key={i} className="border-b border-gray-100">
            {cells.map((cell, j) => (
              <td key={j} className="px-3 py-1.5 text-sm text-gray-700">{cell.trim()}</td>
            ))}
          </tr>
        );
      }
    } else {
      if (inTable) {
        elements.push(
          <div key={`table-${tableKey++}`} className="overflow-x-auto my-3">
            <table className="w-full border border-gray-200 rounded">
              {tableRows}
            </table>
          </div>
        );
        tableRows = [];
        inTable = false;
      }
      const rendered = renderMarkdown(line);
      if (Array.isArray(rendered)) {
        elements.push(...rendered);
      }
    }
  });

  if (inTable && tableRows.length > 0) {
    elements.push(
      <div key={`table-${tableKey}`} className="overflow-x-auto my-3">
        <table className="w-full border border-gray-200 rounded">
          {tableRows}
        </table>
      </div>
    );
  }

  return (
    <div>
      <Link href="/reports" className="text-sm text-indigo-600 hover:underline mb-4 inline-block">
        ← Back to Reports
      </Link>

      {/* KPI summary bar */}
      <div className="flex gap-6 mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
        <div>
          <p className="text-2xl font-bold text-gray-900">{report.total_tasks}</p>
          <p className="text-xs text-gray-500">Total Tasks</p>
        </div>
        <div>
          <p className="text-2xl font-bold text-green-600">{report.completed}</p>
          <p className="text-xs text-gray-500">Completed</p>
        </div>
        <div>
          <p className="text-2xl font-bold text-red-500">{report.failed}</p>
          <p className="text-xs text-gray-500">Failed</p>
        </div>
        {report.total_tasks > 0 && (
          <div>
            <p className="text-2xl font-bold text-indigo-600">
              {Math.round((report.completed / report.total_tasks) * 100)}%
            </p>
            <p className="text-xs text-gray-500">Success Rate</p>
          </div>
        )}
        <div className="ml-auto text-right">
          <p className="text-xs text-gray-400">Generated</p>
          <p className="text-sm text-gray-600">{new Date(report.generated_at).toLocaleString()}</p>
        </div>
      </div>

      {/* Report body */}
      <div className="prose-sm max-w-none">
        {elements}
      </div>
    </div>
  );
}
