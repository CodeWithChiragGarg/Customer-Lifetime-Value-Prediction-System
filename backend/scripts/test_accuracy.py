import sqlite3
import numpy as np
import pandas as pd
from sklearn.model_selection import KFold
import xgboost as xgb
from sklearn.metrics import r2_score

conn = sqlite3.connect('clv_prediction.db')
query = """
    SELECT
        r.customer_id,
        r.recency,
        r.frequency,
        r.monetary_value,
        CAST(julianday('now') - julianday(c.signup_date) AS INTEGER) AS T
    FROM rfm_features r
    JOIN customers c ON r.customer_id = c.customer_id
    WHERE r.frequency > 0 AND r.monetary_value > 0
"""
df = pd.read_sql(query, conn)

df['target'] = df['monetary_value'] * (df['frequency'] + 1)
q98 = df['target'].quantile(0.98)
clean = df[df['target'] <= q98].copy()

clean['log_monetary'] = np.log1p(clean['monetary_value'])
clean['log_frequency'] = np.log1p(clean['frequency'])
clean['purchase_velocity'] = clean['frequency'] / (clean['recency'] + 1)
clean['tenure_ratio'] = clean['recency'] / (clean['T'] + 1)
clean['avg_order_value'] = clean['monetary_value'] / (clean['frequency'] + 1)

features = ['recency', 'frequency', 'monetary_value', 'T', 'log_monetary', 'log_frequency', 'purchase_velocity', 'tenure_ratio', 'avg_order_value']
X = clean[features]
y = clean['target']

kf = KFold(n_splits=5, shuffle=True, random_state=42)
scores = []

for train_idx, test_idx in kf.split(X):
    X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
    y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]
    
    model = xgb.XGBRegressor(
        n_estimators=180,
        max_depth=5,
        learning_rate=0.06,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_alpha=5.5,
        reg_lambda=4.5,
        random_state=42
    )
    model.fit(X_tr, np.log1p(y_tr))
    p_te = np.expm1(model.predict(X_te))
    scores.append(r2_score(y_te, p_te))

print(f"5-Fold Cross Validation R2 Accuracy: {np.mean(scores)*100:.2f}%")
