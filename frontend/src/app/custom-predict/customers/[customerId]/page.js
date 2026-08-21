"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

export default function CustomCustomer360Page() {
  const params = useParams();
  const router = useRouter();

  const customerId = decodeURIComponent(
    params?.customerId || ""
  );

  const [customer, setCustomer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    try {
      setLoading(true);
      setError(null);

      const storedResult = sessionStorage.getItem(
        "customPredictionResult"
      );

      if (!storedResult) {
        setError(
          "Custom dataset results were not found. Please upload the dataset again."
        );
        return;
      }

      const parsedResult = JSON.parse(storedResult);

      if (
        !parsedResult ||
        !Array.isArray(parsedResult.predictions)
      ) {
        setError(
          "Stored custom prediction data is invalid. Please upload the dataset again."
        );
        return;
      }

      const foundCustomer =
        parsedResult.predictions.find(
          (item) =>
            String(item.customer_id) ===
            String(customerId)
        );

      if (!foundCustomer) {
        setError(
          `Customer ${customerId} was not found in the latest uploaded dataset.`
        );
        return;
      }

      setCustomer(foundCustomer);
    } catch (err) {
      console.error(
        "Custom Customer 360 error:",
        err
      );

      setError(
        "Unable to read the custom customer prediction."
      );
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  // ======================================================
  // Loading
  // ======================================================

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-50 p-8">
        <div className="mx-auto max-w-7xl">
          <p className="text-sm text-slate-500">
            Loading custom customer profile...
          </p>
        </div>
      </main>
    );
  }

  // ======================================================
  // Error
  // ======================================================

  if (error) {
    return (
      <main className="min-h-screen bg-slate-50 p-8">
        <div className="mx-auto max-w-7xl">
          <button
            type="button"
            onClick={() =>
              router.push("/custom-predict")
            }
            className="mb-6 text-sm font-medium text-blue-600 hover:underline"
          >
            ← Back to Custom Predictions
          </button>

          <div className="rounded-2xl border border-red-200 bg-red-50 p-6">
            <h2 className="font-semibold text-red-700">
              Unable to load customer
            </h2>

            <p className="mt-2 text-sm text-red-600">
              {error}
            </p>
          </div>
        </div>
      </main>
    );
  }

  if (!customer) {
    return null;
  }

  // ======================================================
  // Customer Calculations
  // ======================================================

  const churnPercent =
    customer.churn_probability !== null &&
    customer.churn_probability !== undefined
      ? Number(customer.churn_probability) * 100
      : null;

  const riskLevel = getRiskLevel(
    customer.churn_probability
  );

  const recommendedAction =
    getRecommendedAction(
      customer.clv_tier,
      riskLevel
    );

  // ======================================================
  // UI
  // ======================================================

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-8">
      <div className="mx-auto max-w-7xl">
        {/* Back Button */}

        <button
          type="button"
          onClick={() =>
            router.push("/custom-predict")
          }
          className="mb-6 text-sm font-medium text-blue-600 hover:underline"
        >
          ← Back to Custom Predictions
        </button>

        {/* Header */}

        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <p className="text-sm font-medium uppercase tracking-wide text-slate-500">
                Customer 360
              </p>

              <span className="rounded-full bg-purple-100 px-3 py-1 text-xs font-semibold text-purple-700">
                Custom Dataset
              </span>
            </div>

            <h1 className="text-3xl font-bold text-slate-900">
              Customer {customer.customer_id}
            </h1>

            <p className="mt-2 text-sm text-slate-500">
              Dynamically generated from the latest
              uploaded dataset
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <span
              className={`rounded-full px-4 py-2 text-sm font-semibold ${getTierStyle(
                customer.clv_tier
              )}`}
            >
              {customer.clv_tier || "Unknown"} Value
            </span>

            <span
              className={`rounded-full px-4 py-2 text-sm font-semibold ${getRiskStyle(
                riskLevel
              )}`}
            >
              {riskLevel}
            </span>
          </div>
        </div>

        {/* KPI Cards */}

        <div className="mb-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            title="Predicted 90-Day CLV"
            value={formatCurrency(
              customer.predicted_clv_90d
            )}
            subtitle="Model-generated customer value"
          />

          <MetricCard
            title="Churn Risk"
            value={
              churnPercent !== null
                ? `${churnPercent.toFixed(1)}%`
                : "N/A"
            }
            subtitle={riskLevel}
          />

          <MetricCard
            title="Average Purchase Value"
            value={formatCurrency(
              customer.monetary_value
            )}
            subtitle="Average transaction amount"
          />

          <MetricCard
            title="Repeat Purchases"
            value={
              customer.frequency !== null &&
              customer.frequency !== undefined
                ? customer.frequency
                : "N/A"
            }
            subtitle="Customer purchase frequency"
          />
        </div>

        {/* Main Information */}

        <div className="mb-8 grid gap-6 lg:grid-cols-2">
          {/* Customer Behaviour */}

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-slate-900">
                Customer Behaviour
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                Features generated from the uploaded
                dataset
              </p>
            </div>

            <div className="space-y-5">
              <InfoRow
                label="Recency"
                value={
                  customer.recency !== null &&
                  customer.recency !== undefined
                    ? `${customer.recency} days`
                    : "N/A"
                }
              />

              <InfoRow
                label="Frequency"
                value={
                  customer.frequency !== null &&
                  customer.frequency !== undefined
                    ? customer.frequency
                    : "N/A"
                }
              />

              <InfoRow
                label="Monetary Value"
                value={formatCurrency(
                  customer.monetary_value
                )}
              />

              <InfoRow
                label="Customer Tenure"
                value={
                  customer.tenure !== null &&
                  customer.tenure !== undefined
                    ? `${customer.tenure} days`
                    : "N/A"
                }
              />
            </div>
          </section>

          {/* Customer Insight */}

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-slate-900">
                Customer Insight
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                Business interpretation of the
                customer&apos;s CLV and churn profile
              </p>
            </div>

            <div className="rounded-xl bg-slate-50 p-5">
              <p className="text-sm font-medium text-slate-500">
                Recommended Action
              </p>

              <p className="mt-2 text-xl font-semibold text-slate-900">
                {recommendedAction}
              </p>
            </div>

            <div className="mt-5 text-sm leading-6 text-slate-600">
              {getCustomerInsight(
                customer.clv_tier,
                riskLevel
              )}
            </div>
          </section>
        </div>

        {/* Model / Source Information */}

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">
                Prediction Source
              </h2>

              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
                This customer profile was generated
                dynamically from the latest uploaded
                dataset. The customer is not required
                to exist in the application&apos;s
                permanent customer database.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
                XGBoost
              </span>

              <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                BG/NBD
              </span>

              <span className="rounded-full bg-purple-50 px-3 py-1 text-xs font-semibold text-purple-700">
                Custom Dataset
              </span>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}


// ========================================================
// Reusable Components
// ========================================================

function MetricCard({
  title,
  value,
  subtitle,
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <p className="text-sm font-medium text-slate-500">
        {title}
      </p>

      <p className="mt-2 text-2xl font-bold text-slate-900">
        {value}
      </p>

      <p className="mt-2 text-xs text-slate-400">
        {subtitle}
      </p>
    </div>
  );
}


function InfoRow({
  label,
  value,
}) {
  return (
    <div className="flex items-center justify-between border-b border-slate-100 pb-4 last:border-none">
      <span className="text-sm text-slate-500">
        {label}
      </span>

      <span className="text-sm font-semibold text-slate-900">
        {value}
      </span>
    </div>
  );
}


// ========================================================
// Business Logic
// ========================================================

function getRiskLevel(probability) {
  if (
    probability === null ||
    probability === undefined
  ) {
    return "Unknown Risk";
  }

  const value = Number(probability);

  if (value >= 0.7) {
    return "High Risk";
  }

  if (value >= 0.3) {
    return "Medium Risk";
  }

  return "Low Risk";
}


function getRecommendedAction(
  tier,
  risk
) {
  if (
    tier === "High" &&
    risk === "High Risk"
  ) {
    return "Priority retention campaign";
  }

  if (
    tier === "High" &&
    risk === "Medium Risk"
  ) {
    return "Offer personalized loyalty incentive";
  }

  if (
    tier === "High" &&
    risk === "Low Risk"
  ) {
    return "VIP and loyalty program opportunity";
  }

  if (risk === "High Risk") {
    return "Run re-engagement campaign";
  }

  if (tier === "Medium") {
    return "Encourage repeat purchases";
  }

  return "Standard customer engagement";
}


function getCustomerInsight(
  tier,
  risk
) {
  if (
    tier === "High" &&
    risk === "Low Risk"
  ) {
    return (
      <p>
        This customer combines strong predicted value
        with relatively low churn risk. Focus on
        loyalty benefits, personalized offers and
        long-term relationship building.
      </p>
    );
  }

  if (
    tier === "High" &&
    risk === "Medium Risk"
  ) {
    return (
      <p>
        This customer has strong predicted value with
        moderate churn risk. A personalized loyalty
        incentive may help protect future customer
        value.
      </p>
    );
  }

  if (
    tier === "High" &&
    risk === "High Risk"
  ) {
    return (
      <p>
        This is a potentially valuable customer with
        elevated churn risk. Retention should be
        prioritized before pursuing additional
        revenue.
      </p>
    );
  }

  if (risk === "High Risk") {
    return (
      <p>
        This customer shows elevated churn risk.
        Consider a re-engagement campaign or targeted
        incentive based on purchasing behaviour.
      </p>
    );
  }

  if (tier === "Medium") {
    return (
      <p>
        This customer has moderate predicted value.
        Repeat-purchase campaigns may help increase
        future customer value.
      </p>
    );
  }

  return (
    <p>
      Continue monitoring this customer&apos;s
      purchasing behaviour and use targeted
      engagement when appropriate.
    </p>
  );
}


// ========================================================
// Styling
// ========================================================

function getTierStyle(tier) {
  if (tier === "High") {
    return "bg-purple-100 text-purple-700";
  }

  if (tier === "Medium") {
    return "bg-blue-100 text-blue-700";
  }

  if (tier === "Low") {
    return "bg-slate-100 text-slate-700";
  }

  return "bg-gray-100 text-gray-600";
}


function getRiskStyle(risk) {
  if (risk === "High Risk") {
    return "bg-red-100 text-red-700";
  }

  if (risk === "Medium Risk") {
    return "bg-amber-100 text-amber-700";
  }

  if (risk === "Low Risk") {
    return "bg-green-100 text-green-700";
  }

  return "bg-gray-100 text-gray-600";
}


// ========================================================
// Formatting
// ========================================================

function formatCurrency(value) {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(Number(value))
  ) {
    return "N/A";
  }

  return new Intl.NumberFormat(
    "en-US",
    {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 2,
    }
  ).format(Number(value));
}