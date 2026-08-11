"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from "recharts";

/**
 * Revenue Forecast line/area chart.
 * Groups predictions by churn probability to simulate a time-based forecast.
 */
export default function RevenueForecastChart({ predictions = [] }) {
  // Create a simulated monthly forecast from predictions
  // Sort by CLV descending and simulate monthly accrual
  const sorted = [...predictions]
    .filter((p) => p.predicted_clv_90d != null)
    .sort((a, b) => (b.predicted_clv_90d || 0) - (a.predicted_clv_90d || 0));

  const totalCLV = sorted.reduce((sum, p) => sum + (p.predicted_clv_90d || 0), 0);

  // Distribute across 6 months with a growth curve
  const months = ["Month 1", "Month 2", "Month 3", "Month 4", "Month 5", "Month 6"];
  const distribution = [0.1, 0.15, 0.18, 0.2, 0.19, 0.18];

  const data = months.map((month, i) => ({
    month,
    revenue: Math.round(totalCLV * distribution[i]),
    cumulative: Math.round(
      totalCLV * distribution.slice(0, i + 1).reduce((a, b) => a + b, 0)
    ),
  }));

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="glass rounded-lg px-4 py-2.5 shadow-lg">
        <p className="text-sm font-semibold text-gray-900">{label}</p>
        <p className="text-sm text-brand-600">
          Revenue: ${payload[0]?.value?.toLocaleString()}
        </p>
        {payload[1] && (
          <p className="text-sm text-emerald-600">
            Cumulative: ${payload[1]?.value?.toLocaleString()}
          </p>
        )}
      </div>
    );
  };

  return (
    <div className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
      <h3 className="mb-1 text-base font-semibold text-gray-900">
        Revenue Forecast
      </h3>
      <p className="mb-6 text-sm text-gray-400">
        Projected revenue from predicted CLV over 6 months
      </p>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id="gradientRevenue" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#4F46E5" stopOpacity={0.2} />
                <stop offset="100%" stopColor="#4F46E5" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradientCumulative" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#10B981" stopOpacity={0.15} />
                <stop offset="100%" stopColor="#10B981" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" vertical={false} />
            <XAxis
              dataKey="month"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 12, fill: "#9CA3AF" }}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 12, fill: "#9CA3AF" }}
              tickFormatter={(v) => `$${(v / 1000).toFixed(0)}K`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="revenue"
              stroke="#4F46E5"
              strokeWidth={2.5}
              fill="url(#gradientRevenue)"
              dot={{ r: 4, fill: "#4F46E5", strokeWidth: 2, stroke: "#fff" }}
              activeDot={{ r: 6, fill: "#4F46E5" }}
            />
            <Area
              type="monotone"
              dataKey="cumulative"
              stroke="#10B981"
              strokeWidth={2}
              strokeDasharray="5 5"
              fill="url(#gradientCumulative)"
              dot={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
