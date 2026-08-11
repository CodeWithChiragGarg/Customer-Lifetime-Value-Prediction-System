"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

/**
 * CLV Distribution bar chart — shows count of customers in CLV buckets.
 */
export default function CLVDistributionChart({ predictions = [] }) {
  // Group predictions into CLV buckets
  const buckets = [
    { range: "$0–50", min: 0, max: 50 },
    { range: "$50–100", min: 50, max: 100 },
    { range: "$100–200", min: 100, max: 200 },
    { range: "$200–500", min: 200, max: 500 },
    { range: "$500–1K", min: 500, max: 1000 },
    { range: "$1K+", min: 1000, max: Infinity },
  ];

  const data = buckets.map((bucket) => ({
    range: bucket.range,
    count: predictions.filter(
      (p) =>
        (p.predicted_clv_90d || 0) >= bucket.min &&
        (p.predicted_clv_90d || 0) < bucket.max
    ).length,
  }));

  const COLORS = ["#E0E7FF", "#C7D2FE", "#A5B4FC", "#818CF8", "#6366F1", "#4F46E5"];

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="glass rounded-lg px-4 py-2.5 shadow-lg">
        <p className="text-sm font-semibold text-gray-900">{label}</p>
        <p className="text-sm text-brand-600">
          {payload[0].value} customers
        </p>
      </div>
    );
  };

  return (
    <div className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
      <h3 className="mb-1 text-base font-semibold text-gray-900">
        CLV Distribution
      </h3>
      <p className="mb-6 text-sm text-gray-400">
        Customer count by predicted 90-day value
      </p>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} barCategoryGap="20%">
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" vertical={false} />
            <XAxis
              dataKey="range"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 12, fill: "#9CA3AF" }}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 12, fill: "#9CA3AF" }}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(79, 70, 229, 0.04)" }} />
            <Bar dataKey="count" radius={[8, 8, 0, 0]}>
              {data.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
