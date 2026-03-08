"use client";

import { useState } from "react";
import TransactionsTable from "@/components/finance/TransactionsTable";
import BusinessSummaryPanel from "@/components/finance/BusinessSummaryPanel";
import FinanceChat from "@/components/finance/FinanceChat";

type Tab = "transactions" | "business" | "chat";

const TABS: { id: Tab; label: string }[] = [
  { id: "transactions", label: "Transactions" },
  { id: "business", label: "Business Details" },
  { id: "chat", label: "Finance Chat" },
];

export default function FinancePage() {
  const [activeTab, setActiveTab] = useState<Tab>("transactions");

  return (
    <div className="flex-1 bg-gray-950 text-gray-100 min-h-screen">
      <div className="max-w-6xl mx-auto p-6 space-y-6">
        {/* Page header */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-emerald-900 flex items-center justify-center">
            <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-bold">Financial Assistant</h1>
            <p className="text-xs text-gray-400">Transactions · Business health · AI finance chat</p>
          </div>
        </div>

        {/* Tab buttons */}
        <div className="flex gap-1 bg-gray-900 rounded-lg p-1 w-fit border border-gray-800">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-5 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? "bg-emerald-700 text-white"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          {activeTab === "transactions" && <TransactionsTable />}
          {activeTab === "business" && <BusinessSummaryPanel />}
          {activeTab === "chat" && <FinanceChat />}
        </div>
      </div>
    </div>
  );
}
