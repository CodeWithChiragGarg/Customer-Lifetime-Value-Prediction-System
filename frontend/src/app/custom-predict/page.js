"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { predictCustomDataset } from "@/lib/api";

const SAMPLE_CSV = `customer_id,recency,frequency,monetary_value,tenure
CUST_101,12,8,145.50,365
CUST_102,45,2,48.00,120
CUST_103,3,15,320.75,450
CUST_104,180,1,25.00,200
CUST_105,7,22,510.00,600
CUST_106,2,30,890.20,730
CUST_107,95,3,65.40,300
CUST_108,14,11,210.00,400
CUST_109,210,0,0.00,250
CUST_110,5,19,430.60,520
CUST_111,60,4,115.80,310
CUST_112,8,14,340.25,480
CUST_113,1,42,1250.00,800
CUST_114,120,2,55.00,220
CUST_115,19,9,185.30,380
`;

export default function CustomPredictPage() {
  const router = useRouter(); 
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState("ALL");
  const [sortField, setSortField] = useState("predicted_clv_90d");
  const [sortAsc, setSortAsc] = useState(false);
  const [selectedIds, setSelectedIds] = useState(new Set());

  const handleFileUpload = async (uploadFile) => {
    if (!uploadFile) return;
    setFile(uploadFile);
    setError(null);
    setSelectedIds(new Set());

    if (uploadFile.size === 0) {
      setError("Selected file is empty (0.0 KB). Please select a CSV file containing customer data, or click '⚡ Load Sample CSV Dataset'.");
      setResult(null);
      setLoading(false);
      return;
    }

    setLoading(true);

    const formData = new FormData();
    formData.append("file", uploadFile);

    try {
      const data = await predictCustomDataset(formData);

setResult(data);

sessionStorage.setItem(
  "customPredictionResult",
  JSON.stringify(data)
);
      setResult(data);
    } catch (err) {
      setError(err.message || "Failed to process dataset");
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadSample = () => {
    const blob = new Blob([SAMPLE_CSV], { type: "text/csv" });
    const sampleFile = new File([blob], "sample_customers.csv", { type: "text/csv" });
    handleFileUpload(sampleFile);
  };

  const handleExportCSV = () => {
    if (!result || !result.predictions.length) return;
    const targetDataset = selectedIds.size > 0
      ? result.predictions.filter((p) => selectedIds.has(p.customer_id))
      : result.predictions;

    const headers = [
      "Customer ID",
      "Recency (Days)",
      "Frequency",
      "Monetary Value ($)",
      "Tenure (Days)",
      "Predicted 90d CLV ($)",
      "Churn Risk (%)",
      "CLV Tier",
    ];
    const rows = targetDataset.map((p) => [
      p.customer_id,
      p.recency,
      p.frequency,
      p.monetary_value,
      p.tenure,
      p.predicted_clv_90d,
      (p.churn_probability * 100).toFixed(1) + "%",
      p.clv_tier,
    ]);

    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `CLV_Predictions_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Filtering & Sorting
  const filteredPredictions = result
    ? result.predictions.filter((item) => {
        const matchesSearch = item.customer_id
          .toLowerCase()
          .includes(search.toLowerCase());
        const matchesTier =
          tierFilter === "ALL" ||
          (item.clv_tier && item.clv_tier.toUpperCase() === tierFilter.toUpperCase());
        return matchesSearch && matchesTier;
      })
    : [];

  const sortedPredictions = [...filteredPredictions].sort((a, b) => {
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

  const handleSort = (field) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === sortedPredictions.length && sortedPredictions.length > 0) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(sortedPredictions.map((p) => p.customer_id)));
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

  const allSelected = sortedPredictions.length > 0 && selectedIds.size === sortedPredictions.length;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Custom Dataset CLV Prediction</h1>
        <p className="mt-1 text-sm text-gray-500">
          Upload your own customer RFM or Transaction CSV dataset to get instant 90-day Customer Lifetime Value predictions and Churn Risk analysis.
        </p>
      </div>

      {/* Upload Zone & Instructions */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Upload Card */}
        <div className="lg:col-span-2 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Upload Dataset File</h2>
          <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 p-8 text-center hover:border-brand-500 transition-colors">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-600 mb-3">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
              </svg>
            </div>
            <p className="text-sm font-medium text-gray-900">Drag & drop your CSV file here</p>
            <p className="text-xs text-gray-500 mt-1">Supports standard CSV files (.csv)</p>

            <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
              <label className="cursor-pointer rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow hover:bg-brand-700 transition-colors">
                Choose CSV File
                <input
                  type="file"
                  accept=".csv,.tsv,.txt,.xlsx,*"
                  className="hidden"
                  onChange={(e) => handleFileUpload(e.target.files[0])}
                />
              </label>
              <button
                onClick={handleLoadSample}
                className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                ⚡ Load Sample CSV Dataset
              </button>
            </div>

            {file && (
              <p className="mt-3 text-xs font-medium text-brand-700">
                Selected: {file.name} ({(file.size / 1024).toFixed(1)} KB)
              </p>
            )}
          </div>
        </div>

        {/* Expected Format Specs */}
        <div className="rounded-xl border border-gray-200 bg-gray-50 p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-2">Supported CSV Headers</h3>
          <p className="text-xs text-gray-600 mb-3">
            Your CSV can be in either RFM format or Transaction format:
          </p>

          <div className="space-y-3 text-xs">
            <div className="rounded-md border border-gray-200 bg-white p-3">
              <span className="font-semibold text-brand-700 block mb-1">Option A: RFM Format</span>
              <code className="text-gray-700 block bg-gray-100 p-1.5 rounded text-[11px]">
                customer_id, recency, frequency, monetary_value, tenure
              </code>
            </div>

            <div className="rounded-md border border-gray-200 bg-white p-3">
              <span className="font-semibold text-brand-700 block mb-1">Option B: Transactions Format</span>
              <code className="text-gray-700 block bg-gray-100 p-1.5 rounded text-[11px]">
                customer_id, timestamp, amount
              </code>
            </div>
          </div>
        </div>
      </div>

      {/* Loading Spinner */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-600 border-t-transparent"></div>
          <span className="ml-3 text-sm font-medium text-gray-600">Running ML feature engineering & ensemble predictions...</span>
        </div>
      )}

      {/* Error Alert */}
      {error && (
        <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700 border border-red-200">
          <strong className="font-semibold">Upload Error:</strong> {error}
        </div>
      )}

      {/* Results Section */}
      {result && !loading && (
        <div className="space-y-6">
          {/* Summary KPI Cards */}
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-5">
            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-medium text-gray-500">Total Customers</p>
              <p className="mt-2 text-2xl font-bold text-gray-900">{result.summary.total_customers}</p>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-medium text-gray-500">Avg Predicted 90d CLV</p>
              <p className="mt-2 text-2xl font-bold text-brand-600">${result.summary.average_clv.toLocaleString()}</p>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-medium text-gray-500">Total Forecast Revenue</p>
              <p className="mt-2 text-2xl font-bold text-emerald-600">${result.summary.total_future_clv.toLocaleString()}</p>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-medium text-gray-500">Avg Churn Risk</p>
              <p className="mt-2 text-2xl font-bold text-amber-600">{(result.summary.average_churn_risk * 100).toFixed(1)}%</p>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-medium text-gray-500">High Tier Customers</p>
              <p className="mt-2 text-2xl font-bold text-purple-600">{result.summary.high_value_count}</p>
            </div>
          </div>

          {/* Results Table Header & Controls */}
          <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
            <div className="flex flex-col gap-4 border-b border-gray-200 p-5 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-base font-semibold text-gray-900">Custom Dataset Prediction Results</h2>
                <p className="text-xs text-gray-500">Showing {sortedPredictions.length} processed customer predictions</p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                {/* Search Input */}
                <input
                  type="text"
                  placeholder="Search Customer ID..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs focus:border-brand-500 focus:outline-none"
                />

                {/* Tier Filter Select Dropdown */}
                <div className="flex items-center gap-1.5">
                  <label className="text-xs font-medium text-gray-600">Filter Tier:</label>
                  <select
                    value={tierFilter}
                    onChange={(e) => setTierFilter(e.target.value)}
                    className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-700 focus:border-brand-500 focus:outline-none bg-white cursor-pointer"
                  >
                    <option value="ALL">All Tiers</option>
                    <option value="HIGH">High Tier</option>
                    <option value="MEDIUM">Medium Tier</option>
                    <option value="LOW">Low Tier</option>
                  </select>
                </div>

                {/* Export CSV Button */}
                <button
                  onClick={handleExportCSV}
                  className="rounded-lg bg-brand-600 px-3.5 py-1.5 text-xs font-medium text-white shadow hover:bg-brand-700 transition-colors flex items-center gap-1.5"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                  </svg>
                  Export {selectedIds.size > 0 ? `(${selectedIds.size})` : "All"} CSV
                </button>
              </div>
            </div>

            {selectedIds.size > 0 && (
              <div className="bg-brand-50 px-6 py-2 flex items-center justify-between border-b border-brand-100 text-xs font-medium text-brand-800">
                <span>{selectedIds.size} customer row(s) selected</span>
                <button
                  onClick={() => setSelectedIds(new Set())}
                  className="text-brand-600 hover:underline text-[11px]"
                >
                  Clear Selection
                </button>
              </div>
            )}

            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-gray-600">
                <thead className="bg-gray-50 border-b border-gray-200 text-gray-700 uppercase font-semibold">
                  <tr>
                    <th className="px-4 py-3 w-10 text-center">
                      <input
                        type="checkbox"
                        checked={allSelected}
                        onChange={toggleSelectAll}
                        className="rounded border-gray-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
                      />
                    </th>
                    <th className="px-4 py-3 cursor-pointer select-none hover:text-gray-900" onClick={() => handleSort("customer_id")}>
                      Customer ID {sortField === "customer_id" && (sortAsc ? "↑" : "↓")}
                    </th>
                    <th className="px-4 py-3 cursor-pointer select-none hover:text-gray-900" onClick={() => handleSort("recency")}>
                      Recency (days) {sortField === "recency" && (sortAsc ? "↑" : "↓")}
                    </th>
                    <th className="px-4 py-3 cursor-pointer select-none hover:text-gray-900" onClick={() => handleSort("frequency")}>
                      Frequency {sortField === "frequency" && (sortAsc ? "↑" : "↓")}
                    </th>
                    <th className="px-4 py-3 cursor-pointer select-none hover:text-gray-900" onClick={() => handleSort("monetary_value")}>
                      Monetary Avg {sortField === "monetary_value" && (sortAsc ? "↑" : "↓")}
                    </th>
                    <th className="px-4 py-3 cursor-pointer select-none hover:text-gray-900" onClick={() => handleSort("tenure")}>
                      Tenure (days) {sortField === "tenure" && (sortAsc ? "↑" : "↓")}
                    </th>
                    <th className="px-4 py-3 cursor-pointer select-none hover:text-gray-900 text-right" onClick={() => handleSort("predicted_clv_90d")}>
                      Predicted 90d CLV {sortField === "predicted_clv_90d" && (sortAsc ? "↑" : "↓")}
                    </th>
                    <th className="px-4 py-3 cursor-pointer select-none hover:text-gray-900 text-right" onClick={() => handleSort("churn_probability")}>
                      Churn Risk {sortField === "churn_probability" && (sortAsc ? "↑" : "↓")}
                    </th>
                    <th className="px-4 py-3 cursor-pointer select-none hover:text-gray-900" onClick={() => handleSort("clv_tier")}>
                      CLV Tier {sortField === "clv_tier" && (sortAsc ? "↑" : "↓")}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white">
                  {sortedPredictions.map((row) => {
                    const isSelected = selectedIds.has(row.customer_id);
                    return (
                      <tr
                        key={row.customer_id}
                        className={`transition-colors ${
                          isSelected ? "bg-brand-50/40" : "hover:bg-gray-50"
                        }`}
                      >
                        <td className="px-4 py-3 text-center">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleSelectRow(row.customer_id)}
                            className="rounded border-gray-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
                          />
                        </td>
                        <td className="px-4 py-3">
  <button
    type="button"
    onClick={() =>
      router.push(
        `/custom-predict/customers/${encodeURIComponent(
          row.customer_id
        )}`
      )
    }
    className="font-semibold text-brand-600 hover:text-brand-800 hover:underline"
    title="Open Custom Customer 360"
  >
    {row.customer_id}
  </button>
</td>
                        <td className="px-4 py-3">{row.recency}d</td>
                        <td className="px-4 py-3">{row.frequency}</td>
                        <td className="px-4 py-3">${row.monetary_value.toFixed(2)}</td>
                        <td className="px-4 py-3">{row.tenure}d</td>
                        <td className="px-4 py-3 text-right font-semibold text-brand-700">
                          ${row.predicted_clv_90d.toFixed(2)}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span
                            className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                              row.churn_probability > 0.7
                                ? "bg-red-100 text-red-800"
                                : row.churn_probability > 0.3
                                ? "bg-yellow-100 text-yellow-800"
                                : "bg-green-100 text-green-800"
                            }`}
                          >
                            {(row.churn_probability * 100).toFixed(1)}%
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                              row.clv_tier === "High"
                                ? "bg-purple-100 text-purple-800"
                                : row.clv_tier === "Medium"
                                ? "bg-blue-100 text-blue-800"
                                : "bg-gray-100 text-gray-800"
                            }`}
                          >
                            {row.clv_tier}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );

}
