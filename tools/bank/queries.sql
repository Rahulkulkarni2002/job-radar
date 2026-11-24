-- Bank Financial Ratio Analysis: the SQL queries from Bank.ipynb
-- Run in DuckDB after loading bank_financials.csv as the table 'financials' and creating the 'banks' table.

-- Setup: the banks table
CREATE TABLE banks (ticker VARCHAR, bank_name VARCHAR, bank_type VARCHAR);

INSERT INTO banks VALUES
    ('JPM', 'JPMorgan Chase', 'Universal bank'),
    ('BAC', 'Bank of America', 'Universal bank'),
    ('WFC', 'Wells Fargo', 'Universal bank'),
    ('C', 'Citigroup', 'Universal bank'),
    ('GS', 'Goldman Sachs', 'Investment bank'),
    ('MS', 'Morgan Stanley', 'Investment bank'),
    ('COF', 'Capital One', 'Card lender');

-- Query 1: One Row per Bank and Year
CREATE VIEW bank_year AS
SELECT
    b.ticker,
    b.bank_name,
    b.bank_type,
    f.year,
    SUM(CASE WHEN f.item = 'net_income' THEN f.value_usd END) AS net_income,
    SUM(CASE WHEN f.item = 'net_interest_income' THEN f.value_usd END) AS net_interest_income,
    SUM(CASE WHEN f.item = 'revenue' THEN f.value_usd END) AS revenue,
    SUM(CASE WHEN f.item = 'noninterest_expense' THEN f.value_usd END) AS noninterest_expense,
    SUM(CASE WHEN f.item = 'total_assets' THEN f.value_usd END) AS total_assets,
    SUM(CASE WHEN f.item = 'total_equity' THEN f.value_usd END) AS total_equity
FROM financials AS f
JOIN banks AS b
    ON f.ticker = b.ticker
GROUP BY b.ticker, b.bank_name, b.bank_type, f.year;

-- Query 2: The Five Ratios
CREATE VIEW ratios AS
SELECT
    ticker,
    bank_name,
    bank_type,
    year,
    ROUND(net_income / total_equity * 100, 2) AS roe_pct,
    ROUND(net_income / total_assets * 100, 2) AS roa_pct,
    ROUND(total_assets / total_equity, 2) AS leverage,
    ROUND(noninterest_expense / revenue * 100, 1) AS efficiency_pct,
    ROUND(net_interest_income / total_assets * 100, 2) AS nim_pct
FROM bank_year;

-- Check: ROE = ROA x Leverage
SELECT
    ticker,
    year,
    roe_pct,
    ROUND(roa_pct * leverage, 2) AS roa_times_leverage
FROM ratios
WHERE year = 2025
ORDER BY ticker;

-- Query 3: ROE Rank in Each Year
SELECT
    year,
    ticker,
    roe_pct,
    RANK() OVER (PARTITION BY year ORDER BY roe_pct DESC) AS roe_rank
FROM ratios
ORDER BY year, roe_rank;

-- Query 4: Change in ROE from the Year Before
SELECT
    ticker,
    year,
    roe_pct,
    LAG(roe_pct) OVER (PARTITION BY ticker ORDER BY year) AS roe_last_year,
    ROUND(roe_pct - LAG(roe_pct) OVER (PARTITION BY ticker ORDER BY year), 2) AS change_in_points
FROM ratios
WHERE ticker IN ('JPM', 'GS', 'COF')
ORDER BY ticker, year;

-- Query 5: Where Does Each Bank's ROE Come From?
WITH five_year AS (
    SELECT
        ticker,
        bank_name,
        bank_type,
        ROUND(AVG(roe_pct), 2) AS roe_pct,
        ROUND(AVG(roa_pct), 2) AS roa_pct,
        ROUND(AVG(leverage), 2) AS leverage
    FROM ratios
    GROUP BY ticker, bank_name, bank_type
),
typical AS (
    SELECT MEDIAN(leverage) AS typical_leverage
    FROM five_year
)
SELECT
    f.bank_name,
    f.bank_type,
    f.roe_pct,
    f.roa_pct,
    f.leverage,
    ROUND(f.roa_pct * t.typical_leverage, 2) AS roe_at_typical_leverage,
    ROUND(f.roe_pct - f.roa_pct * t.typical_leverage, 2) AS points_from_leverage,
    RANK() OVER (ORDER BY f.roe_pct DESC) AS rank_by_roe,
    RANK() OVER (ORDER BY f.roa_pct DESC) AS rank_by_roa
FROM five_year AS f
CROSS JOIN typical AS t
ORDER BY f.roe_pct DESC;

-- Query 6: What Drives ROA? Costs and Lending Margin by Bank Type
SELECT
    bank_type,
    COUNT(DISTINCT ticker) AS banks,
    ROUND(AVG(roa_pct), 2) AS avg_roa_pct,
    ROUND(AVG(efficiency_pct), 1) AS avg_efficiency_pct,
    ROUND(AVG(nim_pct), 2) AS avg_nim_pct,
    ROUND(AVG(leverage), 1) AS avg_leverage
FROM ratios
GROUP BY bank_type
ORDER BY avg_roa_pct DESC;
