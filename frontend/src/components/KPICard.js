"use client";

/**
 * KPI Card component for the dashboard.
 * Displays a metric with label, value, icon, and optional trend.
 */
export default function KPICard({ title, value, icon, trend, color = "brand" }) {
  const colorMap = {
    brand: {
      bg: "bg-brand-50",
      icon: "text-brand-600",
      ring: "ring-brand-100",
    },
    success: {
      bg: "bg-emerald-50",
      icon: "text-emerald-600",
      ring: "ring-emerald-100",
    },
    warning: {
      bg: "bg-amber-50",
      icon: "text-amber-600",
      ring: "ring-amber-100",
    },
    critical: {
      bg: "bg-rose-50",
      icon: "text-rose-600",
      ring: "ring-rose-100",
    },
  };

  const colors = colorMap[color] || colorMap.brand;

  return (
    <div className="card-hover rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-3xl font-bold tracking-tight text-gray-900">
            {value}
          </p>
          {trend && (
            <div className="flex items-center gap-1">
              <span
                className={`text-xs font-semibold ${
                  trend > 0 ? "text-emerald-600" : "text-rose-600"
                }`}
              >
                {trend > 0 ? "↑" : "↓"} {Math.abs(trend)}%
              </span>
              <span className="text-xs text-gray-400">vs last period</span>
            </div>
          )}
        </div>
        <div
          className={`flex h-12 w-12 items-center justify-center rounded-xl ${colors.bg} ring-4 ${colors.ring}`}
        >
          <span className={`text-xl ${colors.icon}`}>{icon}</span>
        </div>
      </div>
    </div>
  );
}
