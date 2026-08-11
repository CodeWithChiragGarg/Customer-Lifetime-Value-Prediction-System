"use client";

/**
 * Filters panel for the Customer Segments view.
 * Provides CLV tier, churn risk range, and tenure filters.
 */
export default function FiltersPanel({ filters, onFilterChange }) {
  const handleChange = (key, value) => {
    onFilterChange({ ...filters, [key]: value });
  };

  return (
    <div className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
      <h3 className="mb-4 text-sm font-semibold text-gray-700 uppercase tracking-wider">
        Filters
      </h3>
      <div className="space-y-5">
        {/* CLV Tier */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-gray-600">
            CLV Tier
          </label>
          <select
            value={filters.clv_tier || ""}
            onChange={(e) => handleChange("clv_tier", e.target.value || null)}
            className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100 transition-colors"
          >
            <option value="">All Tiers</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>
        </div>

        {/* Churn Risk Range */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-gray-600">
            Min Churn Probability
          </label>
          <input
            type="number"
            min="0"
            max="1"
            step="0.1"
            value={filters.min_churn ?? ""}
            onChange={(e) =>
              handleChange("min_churn", e.target.value ? parseFloat(e.target.value) : null)
            }
            placeholder="0.0"
            className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100 transition-colors"
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-gray-600">
            Max Churn Probability
          </label>
          <input
            type="number"
            min="0"
            max="1"
            step="0.1"
            value={filters.max_churn ?? ""}
            onChange={(e) =>
              handleChange("max_churn", e.target.value ? parseFloat(e.target.value) : null)
            }
            placeholder="1.0"
            className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100 transition-colors"
          />
        </div>

        {/* Minimum Tenure */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-gray-600">
            Min Tenure (days)
          </label>
          <input
            type="number"
            min="0"
            step="30"
            value={filters.min_tenure ?? ""}
            onChange={(e) =>
              handleChange("min_tenure", e.target.value ? parseInt(e.target.value) : null)
            }
            placeholder="Any"
            className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100 transition-colors"
          />
        </div>

        {/* Reset Button */}
        <button
          onClick={() =>
            onFilterChange({
              clv_tier: null,
              min_churn: null,
              max_churn: null,
              min_tenure: null,
            })
          }
          className="w-full rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
        >
          Reset Filters
        </button>
      </div>
    </div>
  );
}
