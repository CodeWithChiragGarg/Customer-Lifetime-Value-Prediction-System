"use client";

import { useState, useEffect, useCallback } from "react";
import CustomerTable from "@/components/CustomerTable";
import FiltersPanel from "@/components/FiltersPanel";
import { fetchSegments } from "@/lib/api";

export default function SegmentsPage() {
  const [segments, setSegments] = useState({ total: 0, data: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(0);
  const [filters, setFilters] = useState({
    clv_tier: null,
    min_churn: null,
    max_churn: null,
    min_tenure: null,
  });

  const LIMIT = 25;

  const loadSegments = useCallback(async () => {
    try {
      setLoading(true);
      const params = {
        ...filters,
        limit: LIMIT,
        offset: page * LIMIT,
        sort_by: "predicted_clv_90d",
        sort_order: "desc",
      };
      const data = await fetchSegments(params);
      setSegments(data);
    } catch (err) {
      setError(
        "Unable to connect to the API. Make sure the FastAPI backend is running."
      );
    } finally {
      setLoading(false);
    }
  }, [filters, page]);

  useEffect(() => {
    loadSegments();
  }, [loadSegments]);

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters);
    setPage(0); // Reset to first page on filter change
  };

  const totalPages = Math.ceil(segments.total / LIMIT);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Customer Segments</h2>
        <p className="text-sm text-gray-400 mt-1">
          Filter and explore customer data by CLV tier, churn risk, and tenure
        </p>
      </div>

      {error ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6">
          <div className="flex items-start gap-3">
            <span className="text-xl">⚠️</span>
            <div>
              <h3 className="font-semibold text-amber-800">Connection Error</h3>
              <p className="mt-1 text-sm text-amber-700">{error}</p>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex gap-6">
          {/* Filters Sidebar */}
          <div className="w-64 flex-shrink-0">
            <FiltersPanel filters={filters} onFilterChange={handleFilterChange} />
          </div>

          {/* Main Content */}
          <div className="flex-1 space-y-4">
            {/* Results count */}
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-500">
                Showing{" "}
                <span className="font-semibold text-gray-700">
                  {segments.data.length}
                </span>{" "}
                of{" "}
                <span className="font-semibold text-gray-700">
                  {segments.total}
                </span>{" "}
                customers
              </p>
            </div>

            {/* Data Table */}
            <CustomerTable data={segments.data} loading={loading} />

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 pt-2">
                <button
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  ← Previous
                </button>
                <span className="text-sm text-gray-500">
                  Page {page + 1} of {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                  disabled={page >= totalPages - 1}
                  className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  Next →
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
