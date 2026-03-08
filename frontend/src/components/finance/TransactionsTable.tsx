"use client";

import { useEffect, useState } from "react";
import { getTransactions, syncTransactions, Transaction, TransactionsResponse } from "@/services/api";

export default function TransactionsTable() {
  const [data, setData] = useState<TransactionsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await getTransactions();
      setData(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load transactions");
    } finally {
      setLoading(false);
    }
  }

  async function handleSync() {
    setSyncing(true);
    setSyncResult(null);
    try {
      const res = await syncTransactions();
      setSyncResult(`Synced ${res.synced} new transaction(s). Total: ${res.total}.${res.errors.length ? ` Errors: ${res.errors.join(", ")}` : ""}`);
      await load();
    } catch (e: unknown) {
      setSyncResult(e instanceof Error ? e.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  }

  useEffect(() => { load(); }, []);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-400">
            {data ? `${data.total} transaction(s)` : ""}
            {data?.last_synced ? ` · Last synced: ${new Date(data.last_synced).toLocaleString()}` : ""}
          </p>
        </div>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
        >
          {syncing ? "Syncing..." : "Sync Now"}
        </button>
      </div>

      {syncResult && (
        <div className="p-3 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-300">
          {syncResult}
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-900/30 border border-red-700 rounded-lg text-sm text-red-300">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-16 text-gray-400 text-sm">Loading transactions...</div>
      ) : !data || data.transactions.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-gray-500 text-sm space-y-2">
          <svg className="w-12 h-12 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p>No transactions yet. Click "Sync Now" to pull from emails and files.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-700">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-800 text-gray-400 text-xs uppercase tracking-wide">
                <th className="px-4 py-3 text-left">Date</th>
                <th className="px-4 py-3 text-left">Description</th>
                <th className="px-4 py-3 text-left">Bank</th>
                <th className="px-4 py-3 text-right">Amount</th>
                <th className="px-4 py-3 text-center">Type</th>
                <th className="px-4 py-3 text-center">Source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {data.transactions.map((txn: Transaction) => (
                <tr key={txn.id} className="hover:bg-gray-800/50 transition-colors">
                  <td className="px-4 py-3 text-gray-300 whitespace-nowrap">{txn.date}</td>
                  <td className="px-4 py-3 text-gray-200 max-w-xs truncate" title={txn.description}>
                    {txn.description}
                  </td>
                  <td className="px-4 py-3 text-gray-400">{txn.bank || "—"}</td>
                  <td className={`px-4 py-3 text-right font-medium whitespace-nowrap ${txn.type === "credit" ? "text-emerald-400" : "text-red-400"}`}>
                    {txn.currency} {txn.amount.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                      txn.type === "credit"
                        ? "bg-emerald-900/50 text-emerald-300"
                        : "bg-red-900/50 text-red-300"
                    }`}>
                      {txn.type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="inline-flex px-2 py-0.5 rounded-full text-xs bg-gray-700 text-gray-300">
                      {txn.source}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
