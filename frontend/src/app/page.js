"use client";

import { useState, useEffect } from "react";
import KPICard from "@/components/KPICard";
import CLVDistributionChart from "@/components/CLVDistributionChart";
import RevenueForecastChart from "@/components/RevenueForecastChart";
import { fetchDashboardSummary, fetchPredictions } from "@/lib/api";

export default function DashboardPage() {
  const [summary, setSummary] = useState(null);
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [summaryData, predictionsData] = await Promise.all([
          fetchDashboardSummary(),
          fetchPredictions({ limit: 500 }),
        ]);
        setSummary(summaryData);
        setPredictions(predictionsData);
      } catch (err) {
        setError(
          "Unable to connect to the API. Make sure the FastAPI backend is running on port 8000."
        );
        console.error("Dashboard load error:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
          <p className="text-sm text-gray-400 mt-1">Loading analytics...</p>
        </div>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-32 animate-pulse rounded-2xl bg-gray-100" />
          ))}
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="h-96 animate-pulse rounded-2xl bg-gray-100" />
          <div className="h-96 animate-pulse rounded-2xl bg-gray-100" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
        </div>
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6">
          <div className="flex items-start gap-3">
            <span className="text-xl">⚠️</span>
            <div>
              <h3 className="font-semibold text-amber-800">Connection Error</h3>
              <p className="mt-1 text-sm text-amber-700">{error}</p>
              <div className="mt-3 rounded-lg bg-amber-100/50 p-3">
                <p className="text-xs font-mono text-amber-800">
                  cd backend && python -m app.main
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
        <p className="text-sm text-gray-400 mt-1">
          Customer Lifetime Value analytics overview
        </p>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div className="animate-fade-in">
          <KPICard
            title="Average CLV (90-day)"
            value={`$${summary?.average_clv?.toLocaleString() ?? "0"}`}
            icon="💰"
            color="brand"
          />
        </div>
        <div className="animate-fade-in delay-100">
          <KPICard
            title="Active Customers"
            value={summary?.total_active_customers?.toLocaleString() ?? "0"}
            icon="👥"
            color="success"
          />
        </div>
        <div className="animate-fade-in delay-200">
          <KPICard
            title="Avg Churn Risk"
            value={`${((summary?.average_churn_risk ?? 0) * 100).toFixed(1)}%`}
            icon="⚡"
            color={summary?.average_churn_risk > 0.5 ? "critical" : "warning"}
          />
        </div>
        <div className="animate-fade-in delay-300">
          <KPICard
            title="Total Revenue"
            value={`$${summary?.total_revenue?.toLocaleString() ?? "0"}`}
            icon="📊"
            color="brand"
          />
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="animate-fade-in delay-200">
          <CLVDistributionChart predictions={predictions} />
        </div>
        <div className="animate-fade-in delay-300">
          <RevenueForecastChart predictions={predictions} />
        </div>
      </div>
    </div>
  );
}
