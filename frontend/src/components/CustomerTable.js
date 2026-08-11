"use client";

import { useState } from "react";

/**
 * Customer data table with row selection, column sorting, and CLV tier badges.
 */
export default function CustomerTable({ data = [], loading = false }) {
  const [sortField, setSortField] = useState("predicted_clv_90d");
  const [sortAsc, setSortAsc] = useState(false);
  const [selectedIds, setSelectedIds] = useState(new Set());

  const getTierBadge = (tier) => {
    const styles = {
      High: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200",
      Medium: "bg-amber-50 text-amber-700 ring-1 ring-amber-200",
      Low: "bg-rose-50 text-rose-700 ring-1 ring-rose-200",
    };
    return styles[tier] || "bg-gray-50 text-gray-600 ring-1 ring-gray-200";
  };

  const getChurnIndicator = (prob) => {
    if (prob == null) return { color: "text-gray-400", label: "N/A" };
    if (prob >= 0.7) return { color: "text-rose-600", label: "High Risk" };
    if (prob >= 0.4) return { color: "text-amber-600", label: "Medium" };
    return { color: "text-emerald-600", label: "Low Risk" };
  };

  const handleSort = (field) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === data.length && data.length > 0) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(data.map((c) => c.customer_id)));
    }
  };

  const toggleSelectRow = (id) => {
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedIds(next);
  };

  const sortedData = [...data].sort((a, b) => {
    let valA = a[sortField];
    let valB = b[sortField];

    if (valA == null) return 1;
    if (valB == null) return -1;

    if (typeof valA === "string") valA = valA.toLowerCase();
    if (typeof valB === "string") valB = valB.toLowerCase();

    if (valA < valB) return sortAsc ? -1 : 1;
    if (valA > valB) return sortAsc ? 1 : -1;
    return 0;
  });

  if (loading) {
    return (
      <div className="rounded-2xl border border-gray-100 bg-white p-8 shadow-sm">
        <div className="flex items-center justify-center space-x-3">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
          <span className="text-sm text-gray-500">Loading customer data...</span>
        </div>
      </div>
    );
  }

  const allSelected = data.length > 0 && selectedIds.size === data.length;

  return (
    <div className="rounded-2xl border border-gray-100 bg-white shadow-sm overflow-hidden space-y-2">
      {selectedIds.size > 0 && (
        <div className="bg-brand-50 px-6 py-2 flex items-center justify-between border-b border-brand-100 text-xs font-medium text-brand-800">
          <span>{selectedIds.size} customer(s) selected</span>
          <button
            onClick={() => setSelectedIds(new Set())}
            className="text-brand-600 hover:underline text-[11px]"
          >
            Clear Selection
          </button>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50/50">
              <th className="px-4 py-3.5 w-10 text-center">
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={toggleSelectAll}
                  className="rounded border-gray-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
                />
              </th>
              <th
                onClick={() => handleSort("customer_id")}
                className="px-6 py-3.5 font-semibold text-gray-600 cursor-pointer select-none hover:text-gray-900"
              >
                Customer ID {sortField === "customer_id" && (sortAsc ? "↑" : "↓")}
              </th>
              <th
                onClick={() => handleSort("email")}
                className="px-6 py-3.5 font-semibold text-gray-600 cursor-pointer select-none hover:text-gray-900"
              >
                Email {sortField === "email" && (sortAsc ? "↑" : "↓")}
              </th>
              <th
                onClick={() => handleSort("tenure_days")}
                className="px-6 py-3.5 font-semibold text-gray-600 text-right cursor-pointer select-none hover:text-gray-900"
              >
                Tenure (days) {sortField === "tenure_days" && (sortAsc ? "↑" : "↓")}
              </th>
              <th
                onClick={() => handleSort("total_spent")}
                className="px-6 py-3.5 font-semibold text-gray-600 text-right cursor-pointer select-none hover:text-gray-900"
              >
                Total Spent {sortField === "total_spent" && (sortAsc ? "↑" : "↓")}
              </th>
              <th
                onClick={() => handleSort("predicted_clv_90d")}
                className="px-6 py-3.5 font-semibold text-gray-600 text-right cursor-pointer select-none hover:text-gray-900"
              >
                Predicted CLV {sortField === "predicted_clv_90d" && (sortAsc ? "↑" : "↓")}
              </th>
              <th
                onClick={() => handleSort("clv_tier")}
                className="px-6 py-3.5 font-semibold text-gray-600 text-center cursor-pointer select-none hover:text-gray-900"
              >
                CLV Tier {sortField === "clv_tier" && (sortAsc ? "↑" : "↓")}
              </th>
              <th
                onClick={() => handleSort("churn_probability")}
                className="px-6 py-3.5 font-semibold text-gray-600 text-center cursor-pointer select-none hover:text-gray-900"
              >
                Churn Risk {sortField === "churn_probability" && (sortAsc ? "↑" : "↓")}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {sortedData.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-6 py-12 text-center text-gray-400">
                  No customer data available. Ingest your dataset to see results.
                </td>
              </tr>
            ) : (
              sortedData.map((customer, idx) => {
                const isSelected = selectedIds.has(customer.customer_id);
                const churn = getChurnIndicator(customer.churn_probability);
                return (
                  <tr
                    key={customer.customer_id || idx}
                    className={`transition-colors ${
                      isSelected ? "bg-brand-50/40" : "hover:bg-gray-50/50"
                    }`}
                  >
                    <td className="px-4 py-4 text-center">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelectRow(customer.customer_id)}
                        className="rounded border-gray-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
                      />
                    </td>
                    <td className="px-6 py-4 font-medium text-gray-900">
                      {customer.customer_id}
                    </td>
                    <td className="px-6 py-4 text-gray-500">{customer.email}</td>
                    <td className="px-6 py-4 text-right text-gray-600">
                      {customer.tenure_days ?? "—"}
                    </td>
                    <td className="px-6 py-4 text-right font-medium text-gray-900">
                      ${customer.total_spent?.toLocaleString() ?? "0.00"}
                    </td>
                    <td className="px-6 py-4 text-right font-semibold text-brand-600">
                      ${customer.predicted_clv_90d?.toFixed(2) ?? "—"}
                    </td>
                    <td className="px-6 py-4 text-center">
                      {customer.clv_tier ? (
                        <span
                          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${getTierBadge(customer.clv_tier)}`}
                        >
                          {customer.clv_tier}
                        </span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-center">
                      <div className="flex flex-col items-center gap-1">
                        <span className={`text-xs font-semibold ${churn.color}`}>
                          {churn.label}
                        </span>
                        {customer.churn_probability != null && (
                          <div className="h-1.5 w-16 overflow-hidden rounded-full bg-gray-100">
                            <div
                              className="h-full rounded-full transition-all"
                              style={{
                                width: `${customer.churn_probability * 100}%`,
                                backgroundColor:
                                  customer.churn_probability >= 0.7
                                    ? "#F43F5E"
                                    : customer.churn_probability >= 0.4
                                    ? "#F59E0B"
                                    : "#10B981",
                              }}
                            />
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
