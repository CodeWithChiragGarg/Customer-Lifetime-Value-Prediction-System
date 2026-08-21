"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  fetchCustomer360,
  fetchCustomerExplanation,
} from "@/lib/api";

export default function Customer360Page() {
  const params = useParams();
  const router = useRouter();

  const customerId = params.customerId;

  const [customer, setCustomer] = useState(null);
  const [explanation, setExplanation] = useState(null);

  const [loading, setLoading] = useState(true);
  const [explanationLoading, setExplanationLoading] = useState(true);

  const [error, setError] = useState(null);
  const [explanationError, setExplanationError] = useState(null);

  useEffect(() => {
    async function loadCustomer() {
      try {
        setLoading(true);
        setError(null);

        const data = await fetchCustomer360(customerId);
        setCustomer(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    async function loadExplanation() {
      try {
        setExplanationLoading(true);
        setExplanationError(null);

        const data = await fetchCustomerExplanation(customerId);
        setExplanation(data);
      } catch (err) {
        setExplanationError(err.message);
      } finally {
        setExplanationLoading(false);
      }
    }

    if (customerId) {
      loadCustomer();
      loadExplanation();
    }
  }, [customerId]);

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-50 p-8">
        <div className="mx-auto max-w-7xl">
          <p className="text-slate-500">
            Loading customer profile...
          </p>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen bg-slate-50 p-8">
        <div className="mx-auto max-w-7xl">
          <button
            onClick={() => router.push("/segments")}
            className="mb-6 text-sm font-medium text-blue-600 hover:underline"
          >
            ← Back to Customer Segments
          </button>

          <div className="rounded-xl border border-red-200 bg-red-50 p-6">
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

  const churnPercent =
    customer.churn_probability !== null
      ? customer.churn_probability * 100
      : null;

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-8">
      <div className="mx-auto max-w-7xl">

        {/* Back Button */}

        <button
          onClick={() => router.push("/segments")}
          className="mb-6 text-sm font-medium text-blue-600 hover:underline"
        >
          ← Back to Customer Segments
        </button>

        {/* Customer Header */}

        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="mb-1 text-sm font-medium uppercase tracking-wide text-slate-500">
              Customer 360
            </p>

            <h1 className="text-3xl font-bold text-slate-900">
              Customer {customer.customer_id}
            </h1>

            <p className="mt-1 text-sm text-slate-500">
              {customer.email}
            </p>
          </div>

          <div className="flex gap-3">
            <span className="rounded-full bg-blue-100 px-4 py-2 text-sm font-semibold text-blue-700">
              {customer.clv_tier || "Unknown"} Value
            </span>

            <span
              className={`rounded-full px-4 py-2 text-sm font-semibold ${
                customer.risk_level === "High Risk"
                  ? "bg-red-100 text-red-700"
                  : customer.risk_level === "Medium Risk"
                  ? "bg-amber-100 text-amber-700"
                  : "bg-green-100 text-green-700"
              }`}
            >
              {customer.risk_level || "Unknown Risk"}
            </span>
          </div>
        </div>

        {/* KPI Cards */}

        <div className="mb-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            title="Predicted 90-Day CLV"
            value={formatCurrency(customer.predicted_clv_90d)}
            subtitle="Expected customer value"
          />

          <MetricCard
            title="Churn Risk"
            value={
              churnPercent !== null
                ? `${churnPercent.toFixed(1)}%`
                : "N/A"
            }
            subtitle={customer.risk_level || "Risk unavailable"}
          />

          <MetricCard
            title="Total Spent"
            value={formatCurrency(customer.total_spent)}
            subtitle="Historical revenue"
          />

          <MetricCard
            title="Total Orders"
            value={customer.order_count}
            subtitle="Unique purchase orders"
          />
        </div>

        {/* Purchase Behaviour + Customer Insight */}

        <div className="mb-8 grid gap-6 lg:grid-cols-2">

          {/* Purchase Behaviour */}

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-slate-900">
                Purchase Behaviour
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                Customer purchasing activity across the observation period
              </p>
            </div>

            <div className="space-y-5">
              <InfoRow
                label="Average Order Value"
                value={formatCurrency(customer.average_order_value)}
              />

              <InfoRow
                label="First Purchase"
                value={formatDate(customer.first_purchase)}
              />

              <InfoRow
                label="Last Purchase"
                value={formatDate(customer.last_purchase)}
              />

              <InfoRow
                label="Customer Tenure"
                value={
                  customer.tenure_days !== null
                    ? `${customer.tenure_days} days`
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
                Action suggested from CLV and churn profile
              </p>
            </div>

            <div className="rounded-xl bg-slate-50 p-5">
              <p className="text-sm font-medium text-slate-500">
                Recommended Action
              </p>

              <p className="mt-2 text-xl font-semibold text-slate-900">
                {customer.recommended_action}
              </p>
            </div>

            <div className="mt-5 text-sm leading-6 text-slate-600">
              {customer.clv_tier === "High" &&
                customer.risk_level === "Low Risk" && (
                  <p>
                    This customer combines strong predicted value with
                    low churn risk. Focus on loyalty, VIP benefits and
                    long-term relationship building.
                  </p>
                )}

              {customer.clv_tier === "High" &&
                customer.risk_level === "High Risk" && (
                  <p>
                    This is a valuable customer with elevated churn
                    risk. Prioritize retention before pursuing
                    additional revenue.
                  </p>
                )}

              {customer.clv_tier !== "High" && (
                <p>
                  Use purchase behaviour and churn risk to determine
                  whether this customer should receive re-engagement
                  or repeat-purchase campaigns.
                </p>
              )}
            </div>
          </section>
        </div>

        {/* SHAP Prediction Explainability */}

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">
                Why This Prediction?
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                Key factors influencing the XGBoost CLV prediction
                for this customer
              </p>
            </div>

            <div className="flex gap-2">
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                XGBoost
              </span>

              <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
                SHAP
              </span>
            </div>
          </div>

          {/* Explanation Loading */}

          {explanationLoading && (
            <div className="rounded-xl bg-slate-50 p-5">
              <p className="text-sm text-slate-500">
                Calculating prediction explanation...
              </p>
            </div>
          )}

          {/* Explanation Error */}

          {!explanationLoading && explanationError && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-5">
              <p className="text-sm font-semibold text-amber-800">
                Explanation unavailable
              </p>

              <p className="mt-1 text-sm text-amber-700">
                {explanationError}
              </p>
            </div>
          )}

          {/* SHAP Factors */}

          {!explanationLoading &&
            explanation &&
            explanation.top_factors && (
              <div className="space-y-4">
                {explanation.top_factors.map((factor, index) => (
                  <ShapFactor
                    key={`${factor.feature}-${index}`}
                    factor={factor}
                  />
                ))}

                <div className="mt-6 rounded-xl bg-slate-50 p-4">
                  <p className="text-xs leading-5 text-slate-500">
                    Positive SHAP values push the XGBoost prediction
                    upward. Negative SHAP values push the prediction
                    downward. These values describe relative model
                    influence and are not direct dollar contributions.
                  </p>
                </div>
              </div>
            )}
        </section>
      </div>
    </main>
  );
}


/* =========================================================
   KPI Card
   ========================================================= */

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


/* =========================================================
   Information Row
   ========================================================= */

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


/* =========================================================
   SHAP Factor
   ========================================================= */

function ShapFactor({
  factor,
}) {
  const positive =
    factor.direction === "increases";

  const negative =
    factor.direction === "decreases";

  const absoluteImpact =
    Math.abs(factor.shap_value);

  const barWidth = Math.min(
    absoluteImpact * 65,
    100
  );

  return (
    <div className="rounded-xl border border-slate-100 p-4">
      <div className="mb-3 flex items-start justify-between gap-4">

        {/* Factor Name */}

        <div>
          <div className="flex items-center gap-2">
            <span
              className={`text-lg font-bold ${
                positive
                  ? "text-emerald-600"
                  : negative
                  ? "text-rose-600"
                  : "text-slate-400"
              }`}
            >
              {positive
                ? "↑"
                : negative
                ? "↓"
                : "•"}
            </span>

            <p className="font-semibold text-slate-900">
              {factor.display_name}
            </p>
          </div>

          <p className="mt-1 text-xs text-slate-500">
            Feature value:{" "}
            {formatFeatureValue(
              factor.feature,
              factor.value
            )}
          </p>
        </div>

        {/* Impact */}

        <div className="text-right">
          <p
            className={`text-sm font-semibold ${
              positive
                ? "text-emerald-600"
                : negative
                ? "text-rose-600"
                : "text-slate-500"
            }`}
          >
            {positive
              ? "Increases prediction"
              : negative
              ? "Decreases prediction"
              : "Neutral impact"}
          </p>

          <p className="mt-1 text-xs text-slate-400">
            SHAP{" "}
            {factor.shap_value > 0
              ? "+"
              : ""}
            {factor.shap_value.toFixed(4)}
          </p>
        </div>
      </div>

      {/* Impact Bar */}

      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className={`h-full rounded-full ${
            positive
              ? "bg-emerald-500"
              : negative
              ? "bg-rose-500"
              : "bg-slate-400"
          }`}
          style={{
            width: `${Math.max(
              barWidth,
              3
            )}%`,
          }}
        />
      </div>
    </div>
  );
}


/* =========================================================
   Formatting Helpers
   ========================================================= */

function formatCurrency(value) {
  if (
    value === null ||
    value === undefined
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
  ).format(value);
}


function formatDate(value) {
  if (!value) {
    return "N/A";
  }

  return new Intl.DateTimeFormat(
    "en-US",
    {
      year: "numeric",
      month: "short",
      day: "numeric",
    }
  ).format(
    new Date(value)
  );
}


function formatFeatureValue(
  feature,
  value
) {
  if (
    feature === "monetary_value" ||
    feature === "avg_order_value"
  ) {
    return formatCurrency(value);
  }

  if (feature === "frequency") {
    return `${value} repeat order${
      value === 1 ? "" : "s"
    }`;
  }

  if (
    feature === "recency" ||
    feature === "T"
  ) {
    return `${Math.round(value)} days`;
  }

  return Number(value).toLocaleString(
    "en-US",
    {
      maximumFractionDigits: 4,
    }
  );
}