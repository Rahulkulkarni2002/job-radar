from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

app = FastAPI(title="Customer Churn Prediction API")

# Forward-looking model, the same design as Part 2 of churn.ipynb:
# features come from before a cutoff date, the label from the 90 days after it.
# The model is trained once at startup.
data = pd.read_csv("cleaned_retail.csv")
data["InvoiceDate"] = pd.to_datetime(data["InvoiceDate"])

cutoff = data["InvoiceDate"].max() - pd.Timedelta(days=90)
before = data[data["InvoiceDate"] <= cutoff].copy()
after = data[data["InvoiceDate"] > cutoff]

before["Amount"] = before["Quantity"] * before["Price"]
fwd = before.groupby("Customer ID").agg(
    Frequency=("Invoice", "nunique"),
    Monetary=("Amount", "sum"),
    first_purchase=("InvoiceDate", "min"),
    last_purchase=("InvoiceDate", "max"),
)

fwd["Tenure"] = (fwd["last_purchase"] - fwd["first_purchase"]).dt.days
fwd["AvgOrderValue"] = fwd["Monetary"] / fwd["Frequency"]
fwd["Frequency_log"] = np.log1p(fwd["Frequency"])
fwd["Monetary_log"] = np.log1p(fwd["Monetary"].clip(lower=0))
fwd["Freq_Monetary_Interaction"] = fwd["Frequency"] * fwd["Monetary"]
fwd["Recency"] = (cutoff - fwd["last_purchase"]).dt.days

bought_again = after["Customer ID"].unique()
fwd["Churned"] = (~fwd.index.isin(bought_again)).astype(int)

feature_cols = [
    "Frequency",
    "Monetary",
    "Tenure",
    "AvgOrderValue",
    "Frequency_log",
    "Monetary_log",
    "Freq_Monetary_Interaction",
    "Recency",
]

model = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42)
model.fit(fwd[feature_cols], fwd["Churned"])


# Define the expected input shape for predictions
class CustomerFeatures(BaseModel):
    Frequency: float
    Monetary: float
    Tenure: float
    Recency: float


@app.get("/")
def read_root():
    return {"message": "Customer Churn Prediction API is running"}


@app.post("/predict")
def predict_churn(customer: CustomerFeatures):
    if customer.Frequency <= 0:
        raise HTTPException(status_code=400, detail="Frequency must be greater than 0")
    if customer.Monetary < 0:
        raise HTTPException(status_code=400, detail="Monetary cannot be negative")
    if customer.Tenure < 0:
        raise HTTPException(status_code=400, detail="Tenure cannot be negative")
    if customer.Recency < 0:
        raise HTTPException(status_code=400, detail="Recency cannot be negative")

    features = pd.DataFrame(
        [
            {
                "Frequency": customer.Frequency,
                "Monetary": customer.Monetary,
                "Tenure": customer.Tenure,
                "AvgOrderValue": customer.Monetary / customer.Frequency,
                "Frequency_log": np.log1p(customer.Frequency),
                "Monetary_log": np.log1p(customer.Monetary),
                "Freq_Monetary_Interaction": customer.Frequency * customer.Monetary,
                "Recency": customer.Recency,
            }
        ]
    )[feature_cols]

    prediction = model.predict(features)[0]
    probability = model.predict_proba(features)[0][1]

    return {
        "churned_prediction": int(prediction),
        "churn_probability": float(probability),
    }
