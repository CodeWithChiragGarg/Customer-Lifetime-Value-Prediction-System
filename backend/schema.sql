-- Customer Lifetime Value (CLV) Prediction System
-- Database Schema (PostgreSQL / SQLite compatible)
-- Version: 1.1

-- 1. Customers table
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    signup_date TIMESTAMP NOT NULL
);

-- 2. Transactions table
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id VARCHAR(36) PRIMARY KEY,
    customer_id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- 3. RFM Features table
CREATE TABLE IF NOT EXISTS rfm_features (
    customer_id VARCHAR(255) PRIMARY KEY,
    recency INTEGER NOT NULL,
    frequency INTEGER NOT NULL,
    monetary_value DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- 4. Predictions table
CREATE TABLE IF NOT EXISTS predictions (
    customer_id VARCHAR(255) PRIMARY KEY,
    predicted_clv_90d DECIMAL(10, 2),
    churn_probability FLOAT CHECK (churn_probability >= 0.0 AND churn_probability <= 1.0),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_transactions_customer_id ON transactions(customer_id);
CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp);
