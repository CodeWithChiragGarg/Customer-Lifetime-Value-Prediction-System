const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://customer-lifetime-value-api.onrender.com";

/**
 * Fetch dashboard summary KPIs.
 */
export async function fetchDashboardSummary() {
  const response = await fetch(
    `${API_BASE}/api/v1/dashboard/summary`,
    {
      cache: "no-store",
    }
  );

  if (!response.ok) {
    throw new Error(
      "Failed to fetch dashboard summary"
    );
  }

  return response.json();
}

/**
 * Fetch CLV predictions.
 */
export async function fetchPredictions({
  customerId,
  limit = 50,
  offset = 0,
} = {}) {
  const url = new URL(
    `${API_BASE}/api/v1/predict/clv`
  );

  if (customerId) {
    url.searchParams.set(
      "customer_id",
      customerId
    );
  }

  url.searchParams.set(
    "limit",
    limit.toString()
  );

  url.searchParams.set(
    "offset",
    offset.toString()
  );

  const response = await fetch(
    url.toString(),
    {
      cache: "no-store",
    }
  );

  if (!response.ok) {
    throw new Error(
      "Failed to fetch predictions"
    );
  }

  return response.json();
}

/**
 * Fetch customer segments.
 *
 * Supports filtering, sorting and pagination.
 */
export async function fetchSegments(
  params = {}
) {
  const url = new URL(
    `${API_BASE}/api/v1/segments`
  );

  Object.entries(params).forEach(
    ([key, value]) => {
      if (
        value !== null &&
        value !== undefined &&
        value !== ""
      ) {
        url.searchParams.set(
          key,
          value.toString()
        );
      }
    }
  );

  const response = await fetch(
    url.toString(),
    {
      cache: "no-store",
    }
  );

  if (!response.ok) {
    throw new Error(
      "Failed to fetch customer segments"
    );
  }

  return response.json();
}

/**
 * Fetch Customer 360 information
 * for one customer.
 */
export async function fetchCustomer360(
  customerId
) {
  if (!customerId) {
    throw new Error(
      "Customer ID is required"
    );
  }

  const encodedCustomerId =
    encodeURIComponent(customerId);

  const response = await fetch(
    `${API_BASE}/api/v1/customers/${encodedCustomerId}`,
    {
      cache: "no-store",
    }
  );

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(
        "Customer not found"
      );
    }

    throw new Error(
      "Failed to fetch customer details"
    );
  }

  return response.json();
}

/**
 * Fetch SHAP explanation for the
 * XGBoost component of a customer's
 * CLV prediction.
 */
export async function fetchCustomerExplanation(
  customerId
) {
  if (!customerId) {
    throw new Error(
      "Customer ID is required"
    );
  }

  const encodedCustomerId =
    encodeURIComponent(customerId);

  const response = await fetch(
    `${API_BASE}/api/v1/customers/${encodedCustomerId}/explanation`,
    {
      cache: "no-store",
    }
  );

  if (!response.ok) {
    const errorData = await response
      .json()
      .catch(() => ({}));

    throw new Error(
      errorData.detail ||
        "Failed to fetch prediction explanation"
    );
  }

  return response.json();
}

/**
 * Upload a custom CSV dataset
 * and generate CLV predictions.
 */
export async function predictCustomDataset(
  formData
) {
  const response = await fetch(
    `${API_BASE}/api/v1/predict/custom`,
    {
      method: "POST",
      body: formData,
    }
  );

  if (!response.ok) {
    const errorData = await response
      .json()
      .catch(() => ({}));

    throw new Error(
      errorData.detail ||
        "Failed to process custom dataset"
    );
  }

  return response.json();
}
