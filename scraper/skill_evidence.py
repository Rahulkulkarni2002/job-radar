"""Honest skill credit, built ONLY from Rahul's real resume, GitHub projects and coursework (no invented skills).

SAME  = he has done this; the JD just uses a different word -> full credit (use the JD's word on the resume)
CLOSE = a close equivalent he really has -> half credit (say the real tool, never claim the other one)
Anything else the JD asks for is a true gap -> no credit.
"""
import re

SAME = {
    "hypothesis testing": "A/B group-balance checks + uplift tests (Email Uplift), toss significance (IPL)",
    "predictive analytics": "churn model (81% recall), NRE cost forecasting (Qualcomm)",
    "statistical modeling": "regression, Prophet, statsmodels, RF/XGBoost ensemble",
    "process improvement": "recommended payment-process changes (Inventa)",
    "data warehousing": "Snowflake → Databricks medallion pipeline; SQL & ETL coursework",
    "root cause analysis": "traced UK orders-vs-revenue gap to wholesale accounts (Retail dashboard)",
    "data analysis": "all projects",
    "cohort analysis": "RFM + retention segments (Segmentation project)",
    "model validation": "leave-one-out CV (Qualcomm), leakage check (Churn)",
    "cost analysis": "NRE cost forecasting (Qualcomm)",
}
CLOSE = {
    "power bi": "Tableau", "looker": "Tableau", "qlik": "Tableau", "domo": "Tableau",
    "bigquery": "Snowflake / SQL", "redshift": "Snowflake / SQL", 
    "airflow": "Databricks Jobs orchestration", "dbt": "SQL transforms in medallion pipeline",
    "aws": "learning AWS; Databricks cloud projects", "azure": "Databricks (cloud)", "gcp": "Databricks (cloud)", "s3": "learning AWS", "sagemaker": "MLflow (learning AWS)",
    "deep learning": "neural network (Customer Analytics coursework)",
    "nlp": "text chunking + embeddings + RAG (Omni project)", "mysql": "PostgreSQL (Omni)", "nosql": "pgvector / PostgreSQL (Omni)",
    "r": "Python (pandas/statsmodels)", "sas": "Python stats", "stata": "Python stats", "spss": "Python stats", "matlab": "Python",
    "optimization": "AI & Prescriptive Analytics coursework", "linear programming": "AI & Prescriptive Analytics coursework",
    "simulation": "AI & Prescriptive Analytics coursework",
    "variance analysis": "forecast-vs-actual overrun tracking (Qualcomm)",
    "financial modeling": "cost forecasting model (Qualcomm), ratio analysis (Bank project), Corporate Finance coursework",
    "fp&a": "budget forecasting (Qualcomm), Financial Mgmt coursework", "p&l": "Corporate Finance coursework, bank ratio analysis",
    "product analytics": "churn / retention / segmentation", "funnel analysis": "churn / retention analysis",
    "attribution": "uplift modeling (incremental revenue)",
    "inventory": "inventory planning insight (Retail dashboard)", "supply chain": "demand forecasting (Prophet)",
    "data governance": "data validation, leakage checks, secrets kept out of code",
}
# When the JD names HIS tool too, the other tool is almost always an alternative ("Tableau or Power BI") -> full credit
ALTERNATIVES = [  # NOTE: aws removed from "mine" (learning only)
({"tableau"}, {"power bi", "looker", "qlik", "domo"}), ({"python"}, {"r", "sas", "stata", "spss", "matlab", "scala"}),
                ({"snowflake", "databricks"}, {"bigquery", "redshift"}), ({"sql"}, {"postgresql", "mysql"})]

def credit(want, have):
    """want: JD skill terms; have: set of terms he has. -> (score 0-100, said[(skill, evidence)], close[(skill, evidence)], alts[skill], gaps[skill])"""
    alt_ok = set()
    for mine, others in ALTERNATIVES:
        if want & mine: alt_ok |= (want & others)
    said, close, alts, gaps, pts = [], [], [], [], 0.0
    for k in sorted(want):
        if k in have: pts += 1
        elif k in alt_ok: pts += 1; alts.append(k)          # "Python or R": you meet it with your tool - NOT a claim that you know R
        elif k in SAME: pts += 1; said.append((k, SAME[k]))
        elif k in CLOSE: pts += .5; close.append((k, CLOSE[k]))
        else: gaps.append(k)
    return (round(100 * pts / len(want)) if want else None), said, close, alts, gaps
