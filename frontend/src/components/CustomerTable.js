"use client";

import { useState } from "react";
import Link from "next/link";

/**
 * Customer table with:
 * - Row selection
 * - Column sorting
 * - CLV tier badges
 * - Churn risk indicators
 * - Customer 360 navigation
 */
export default function CustomerTable({
  data = [],
  loading = false,
}) {
  const [sortField, setSortField] = useState("predicted_clv_90d");
  const [sortAsc, setSortAsc] = useState(false);
  const [selectedIds, setSelectedIds] = useState(new Set());

  // -------------------------------------------------------
  // CLV Tier Badge
  // -------------------------------------------------------

  const getTierBadge = (tier) => {
    const styles = {
      High:
        "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200",
      Medium:
        "bg-amber-50 text-amber-700 ring-1 ring-amber-200",
      Low:
        "bg-rose-50 text-rose-700 ring-1 ring-rose-200",
    };

    return (
      styles[tier] ||
      "bg-gray-50 text-gray-600 ring-1 ring-gray-200"
    );
  };

  // -------------------------------------------------------
  // Churn Risk
  // -------------------------------------------------------

  const getChurnIndicator = (probability) => {
    if (probability == null) {
      return {
        color: "text-gray-400",
        label: "N/A",
      };
    }

    if (probability >= 0.7) {
      return {
        color: "text-rose-600",
        label: "High Risk",
      };
    }

    if (probability >= 0.4) {
      return {
        color: "text-amber-600",
        label: "Medium Risk",
      };
    }

    return {
      color: "text-emerald-600",
      label: "Low Risk",
    };
  };

  // -------------------------------------------------------
  // Sorting
  // -------------------------------------------------------

  const handleSort = (field) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  const sortedData = [...data].sort((a, b) => {
    let valueA = a[sortField];
    let valueB = b[sortField];

    if (valueA == null) return 1;
    if (valueB == null) return -1;

    if (typeof valueA === "string") {
      valueA = valueA.toLowerCase();
    }

    if (typeof valueB === "string") {
      valueB = valueB.toLowerCase();
    }

    if (valueA < valueB) {
      return sortAsc ? -1 : 1;
    }

    if (valueA > valueB) {
      return sortAsc ? 1 : -1;
    }

    return 0;
  });

  // -------------------------------------------------------
  // Selection
  // -------------------------------------------------------

  const toggleSelectAll = () => {
    if (
      selectedIds.size === data.length &&
      data.length > 0
    ) {
      setSelectedIds(new Set());
      return;
    }

    setSelectedIds(
      new Set(
        data.map((customer) => customer.customer_id)
      )
    );
  };

  const toggleSelectRow = (customerId) => {
    const next = new Set(selectedIds);

    if (next.has(customerId)) {
      next.delete(customerId);
    } else {
      next.add(customerId);
    }

    setSelectedIds(next);
  };

  // -------------------------------------------------------
  // Loading
  // -------------------------------------------------------

  if (loading) {
    return (
      <div className="rounded-2xl border border-gray-100 bg-white p-8 shadow-sm">
        <div className="flex items-center justify-center space-x-3">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />

          <span className="text-sm text-gray-500">
            Loading customer data...
          </span>
        </div>
      </div>
    );
  }

  const allSelected =
    data.length > 0 &&
    selectedIds.size === data.length;

  return (
    <div className="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-sm">

      {/* Selected customers */}

      {selectedIds.size > 0 && (
        <div className="flex items-center justify-between border-b border-brand-100 bg-brand-50 px-6 py-2 text-xs font-medium text-brand-800">
          <span>
            {selectedIds.size} customer(s) selected
          </span>

          <button
            onClick={() => setSelectedIds(new Set())}
            className="text-[11px] text-brand-600 hover:underline"
          >
            Clear Selection
          </button>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">

          {/* Header */}

          <thead>
            <tr className="border-b border-gray-100 bg-gray-50/50">

              <th className="w-10 px-4 py-3.5 text-center">
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={toggleSelectAll}
                  className="cursor-pointer rounded border-gray-300 text-brand-600 focus:ring-brand-500"
                />
              </th>

              <SortableHeader
                label="Customer ID"
                field="customer_id"
                sortField={sortField}
                sortAsc={sortAsc}
                onSort={handleSort}
              />

              <SortableHeader
                label="Email"
                field="email"
                sortField={sortField}
                sortAsc={sortAsc}
                onSort={handleSort}
              />

              <SortableHeader
                label="Tenure (days)"
                field="tenure_days"
                sortField={sortField}
                sortAsc={sortAsc}
                onSort={handleSort}
                align="right"
              />

              <SortableHeader
                label="Total Spent"
                field="total_spent"
                sortField={sortField}
                sortAsc={sortAsc}
                onSort={handleSort}
                align="right"
              />

              <SortableHeader
                label="Predicted CLV"
                field="predicted_clv_90d"
                sortField={sortField}
                sortAsc={sortAsc}
                onSort={handleSort}
                align="right"
              />

              <SortableHeader
                label="CLV Tier"
                field="clv_tier"
                sortField={sortField}
                sortAsc={sortAsc}
                onSort={handleSort}
                align="center"
              />

              <SortableHeader
                label="Churn Risk"
                field="churn_probability"
                sortField={sortField}
                sortAsc={sortAsc}
                onSort={handleSort}
                align="center"
              />

            </tr>
          </thead>

          {/* Body */}

          <tbody className="divide-y divide-gray-50">

            {sortedData.length === 0 ? (
              <tr>
                <td
                  colSpan={8}
                  className="px-6 py-12 text-center text-gray-400"
                >
                  No customer data available. Ingest your
                  dataset to see results.
                </td>
              </tr>
            ) : (
              sortedData.map((customer, index) => {
                const isSelected =
                  selectedIds.has(customer.customer_id);

                const churn =
                  getChurnIndicator(
                    customer.churn_probability
                  );

                return (
                  <tr
                    key={
                      customer.customer_id || index
                    }
                    className={`transition-colors ${
                      isSelected
                        ? "bg-brand-50/40"
                        : "hover:bg-gray-50/50"
                    }`}
                  >

                    {/* Checkbox */}

                    <td className="px-4 py-4 text-center">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() =>
                          toggleSelectRow(
                            customer.customer_id
                          )
                        }
                        className="cursor-pointer rounded border-gray-300 text-brand-600 focus:ring-brand-500"
                      />
                    </td>

                    {/* CLICKABLE CUSTOMER ID */}

                    <td className="px-6 py-4 font-medium">
                      <Link
                        href={`/customers/${encodeURIComponent(
                          customer.customer_id
                        )}`}
                        className="text-brand-600 transition-colors hover:text-brand-700 hover:underline"
                        title="Open Customer 360"
                      >
                        {customer.customer_id}
                      </Link>
                    </td>

                    {/* Email */}

                    <td className="px-6 py-4 text-gray-500">
                      {customer.email}
                    </td>

                    {/* Tenure */}

                    <td className="px-6 py-4 text-right text-gray-600">
                      {customer.tenure_days ?? "—"}
                    </td>

                    {/* Total Spent */}

                    <td className="px-6 py-4 text-right font-medium text-gray-900">
                      {formatCurrency(
                        customer.total_spent
                      )}
                    </td>

                    {/* Predicted CLV */}

                    <td className="px-6 py-4 text-right font-semibold text-brand-600">
                      {customer.predicted_clv_90d != null
                        ? formatCurrency(
                            customer.predicted_clv_90d
                          )
                        : "—"}
                    </td>

                    {/* CLV Tier */}

                    <td className="px-6 py-4 text-center">
                      {customer.clv_tier ? (
                        <span
                          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${getTierBadge(
                            customer.clv_tier
                          )}`}
                        >
                          {customer.clv_tier}
                        </span>
                      ) : (
                        <span className="text-gray-400">
                          —
                        </span>
                      )}
                    </td>

                    {/* Churn Risk */}

                    <td className="px-6 py-4 text-center">
                      <div className="flex flex-col items-center gap-1">

                        <span
                          className={`text-xs font-semibold ${churn.color}`}
                        >
                          {churn.label}
                        </span>

                        {customer.churn_probability !=
                          null && (
                          <div className="h-1.5 w-16 overflow-hidden rounded-full bg-gray-100">

                            <div
                              className="h-full rounded-full transition-all"
                              style={{
                                width: `${Math.min(
                                  customer.churn_probability *
                                    100,
                                  100
                                )}%`,

                                backgroundColor:
                                  customer.churn_probability >=
                                  0.7
                                    ? "#F43F5E"
                                    : customer.churn_probability >=
                                      0.4
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


/**
 * Reusable sortable column heading.
 */
function SortableHeader({
  label,
  field,
  sortField,
  sortAsc,
  onSort,
  align = "left",
}) {
  const alignments = {
    left: "text-left",
    right: "text-right",
    center: "text-center",
  };

  return (
    <th
      onClick={() => onSort(field)}
      className={`cursor-pointer select-none px-6 py-3.5 font-semibold text-gray-600 hover:text-gray-900 ${alignments[align]}`}
    >
      {label}

      {sortField === field && (
        <span className="ml-1">
          {sortAsc ? "↑" : "↓"}
        </span>
      )}
    </th>
  );
}


/**
 * Display USD currency consistently.
 */
function formatCurrency(value) {
  if (
    value === null ||
    value === undefined
  ) {
    return "$0.00";
  }

  return new Intl.NumberFormat(
    "en-US",
    {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 2,
    }
  ).format(value);
}