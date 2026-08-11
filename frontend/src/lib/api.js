const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Fetch dashboard summary KPIs from the backend.
 * @returns {Promise<{average_clv: number, total_active_customers: number, average_churn_risk: number, total_revenue: number}>}
 */
export async function fetchDashboardSummary() {
  const res = await fetch(`${API_BASE}/api/v1/dashboard/summary`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch dashboard summary");
  return res.json();
}

/**
 * Fetch CLV predictions from the backend.
 * @param {Object} params
 * @param {string} [params.customerId] - Optional customer ID filter
 * @param {number} [params.limit=50]
 * @param {number} [params.offset=0]
 * @returns {Promise<Array>}
 */
export async function fetchPredictions({ customerId, limit = 50, offset = 0 } = {}) {
  const url = new URL(`${API_BASE}/api/v1/predict/clv`);
  if (customerId) url.searchParams.set("customer_id", customerId);
  url.searchParams.set("limit", limit.toString());
  url.searchParams.set("offset", offset.toString());

  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch predictions");
  return res.json();
}

/**
 * Fetch customer segments from the backend.
 * @param {Object} params - Query parameters for filtering and pagination
 * @returns {Promise<{total: number, data: Array}>}
 */
export async function fetchSegments(params = {}) {
  const url = new URL(`${API_BASE}/api/v1/segments`);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") {
      url.searchParams.set(key, value.toString());
    }
  });

  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch segments");
  return res.json();
}

/**
 * Upload custom CSV dataset to compute CLV predictions.
 * @param {FormData} formData
 * @returns {Promise<{summary: Object, predictions: Array}>}
 */
export async function predictCustomDataset(formData) {
  const res = await fetch(`${API_BASE}/api/v1/predict/custom`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to process custom dataset");
  }

  return res.json();
}
