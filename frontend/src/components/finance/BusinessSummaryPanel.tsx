"use client";

import { useEffect, useState } from "react";
import { getBusinessSummary, refreshBusinessSummary, BusinessSummary } from "@/services/api";

export default function BusinessSummaryPanel() {
  const [data, setData] = useState<BusinessSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await getBusinessSummary();
      setData(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load summary");
    } finally {
      setLoading(false);
    }
  }

  async function handleRefresh() {
    setRefreshing(true);
    setError(null);
    try {
      const res = await refreshBusinessSummary();
      setData(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Refresh failed");
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => { load(); }, []);

  const net = data ? data.total_credits - data.total_debits : 0;

  return (
    <div className="space-y-6">
      {/* Stat Cards */}
      {data && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Total Credits</p>
            <p className="text-xl font-bold text-emerald-400">
              PKR {data.total_credits.toLocaleString()}
            </p>
          </div>
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Total Debits</p>
            <p className="text-xl font-bold text-red-400">
              PKR {data.total_debits.toLocaleString()}
            </p>
          </div>
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Net Balance</p>
            <p className={`text-xl font-bold ${net >= 0 ? "text-emerald-400" : "text-red-400"}`}>
              PKR {net.toLocaleString()}
            </p>
          </div>
        </div>
      )}

      {/* Header row */}
      <div className="flex items-center justify-between">
        <div>
          {data && (
            <p className="text-xs text-gray-500">
              {data.transaction_count} transactions · Generated {new Date(data.generated_at).toLocaleString()}
            </p>
          )}
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing || loading}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
        >
          {refreshing ? "Generating..." : "Refresh Analysis"}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-900/30 border border-red-700 rounded-lg text-sm text-red-300">
          {error}
        </div>
      )}

      {/* Summary text */}
      {loading ? (
        <div className="flex items-center justify-center py-16 text-gray-400 text-sm">
          Generating business summary...
        </div>
      ) : data ? (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-5">
          <pre className="whitespace-pre-wrap text-sm text-gray-200 font-sans leading-relaxed">
            {data.summary}
          </pre>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-16 text-gray-500 text-sm space-y-2">
          <p>No summary available. Click "Refresh Analysis" to generate one.</p>
        </div>
      )}
    </div>
  );
}
