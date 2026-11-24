import streamlit as st
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

st.title("Customer Churn Prediction")
st.write(
    "Enter a customer's purchase history to predict how likely they are "
    "to stop buying in the next 90 days."
)

feature_cols = [
    'Frequency', 'Monetary', 'Tenure', 'AvgOrderValue',
    'Frequency_log', 'Monetary_log', 'Freq_Monetary_Interaction', 'Recency',
]


@st.cache_resource
def load_and_train_model():
    # Forward-looking model, the same design as Part 2 of churn.ipynb:
    # features come from before a cutoff date, the label from the 90 days after it.
    data = pd.read_csv('cleaned_retail.csv')
    data['InvoiceDate'] = pd.to_datetime(data['InvoiceDate'])

    cutoff = data['InvoiceDate'].max() - pd.Timedelta(days=90)
    before = data[data['InvoiceDate'] <= cutoff].copy()
    after = data[data['InvoiceDate'] > cutoff]

    before['Amount'] = before['Quantity'] * before['Price']
    fwd = before.groupby('Customer ID').agg(
        Frequency=('Invoice', 'nunique'),
        Monetary=('Amount', 'sum'),
        first_purchase=('InvoiceDate', 'min'),
        last_purchase=('InvoiceDate', 'max'),
    )

    fwd['Tenure'] = (fwd['last_purchase'] - fwd['first_purchase']).dt.days
    fwd['AvgOrderValue'] = fwd['Monetary'] / fwd['Frequency']
    fwd['Frequency_log'] = np.log1p(fwd['Frequency'])
    fwd['Monetary_log'] = np.log1p(fwd['Monetary'].clip(lower=0))
    fwd['Freq_Monetary_Interaction'] = fwd['Frequency'] * fwd['Monetary']
    fwd['Recency'] = (cutoff - fwd['last_purchase']).dt.days

    bought_again = after['Customer ID'].unique()
    fwd['Churned'] = (~fwd.index.isin(bought_again)).astype(int)

    model = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42)
    model.fit(fwd[feature_cols], fwd['Churned'])
    return model


model = load_and_train_model()

frequency = st.number_input("Frequency (number of orders)", min_value=1, value=5)
monetary = st.number_input("Monetary (total spend, £)", min_value=0.0, value=500.0)
tenure = st.number_input("Tenure (days between first and last order)", min_value=0, value=365)
recency = st.number_input("Recency (days since the last order)", min_value=0, value=30)

if st.button("Predict Churn"):
    features = pd.DataFrame([{
        'Frequency': frequency,
        'Monetary': monetary,
        'Tenure': tenure,
        'AvgOrderValue': monetary / frequency,
        'Frequency_log': np.log1p(frequency),
        'Monetary_log': np.log1p(monetary),
        'Freq_Monetary_Interaction': frequency * monetary,
        'Recency': recency,
    }])[feature_cols]

    prediction = model.predict(features)[0]
    probability = model.predict_proba(features)[0][1]

    st.subheader("Result")
    if prediction == 1:
        st.error(f"This customer is likely to stop buying in the next 90 days ({probability:.1%} probability)")
    else:
        st.success(f"This customer is likely to buy again in the next 90 days ({probability:.1%} churn probability)")

    st.progress(float(probability))
