-- Online Retail Sales Performance Analysis: the SQL queries from sales_kpi_analysis.ipynb
-- Run in DuckDB with cleaned_retail.csv loaded as the table 'retail'.
-- Each of these is also calculated in pandas in the notebook, and the results are compared.

-- 1. Monthly Revenue Trend
SELECT
    DATE_TRUNC('month', InvoiceDate) AS Month,
    SUM(Quantity * Price) AS Revenue
FROM retail
GROUP BY Month
ORDER BY Month;

-- Month-over-month growth with LAG
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', InvoiceDate) AS Month,
        SUM(Quantity * Price) AS Revenue
    FROM retail
    WHERE InvoiceDate < '2011-12-01'
    GROUP BY Month
)
SELECT
    Month,
    ROUND(Revenue, 2) AS Revenue,
    ROUND((Revenue - LAG(Revenue) OVER (ORDER BY Month)) / LAG(Revenue) OVER (ORDER BY Month) * 100, 1) AS Growth_Pct
FROM monthly
ORDER BY Month;

-- 2. Top Products: Revenue vs. Quantity
SELECT
    StockCode,
    Description,
    SUM(Quantity * Price) AS Revenue,
    SUM(Quantity) AS Total_Quantity
FROM retail
GROUP BY StockCode, Description
ORDER BY Revenue DESC
LIMIT 10;

-- 2. Top Products: Revenue vs. Quantity
SELECT
    StockCode,
    Description,
    SUM(Quantity * Price) AS Revenue,
    SUM(Quantity) AS Total_Quantity
FROM retail
WHERE StockCode NOT IN ('POST', 'DOT', 'C2')
GROUP BY StockCode, Description
ORDER BY Revenue DESC
LIMIT 10;

-- 2. Top Products: Revenue vs. Quantity
SELECT
    StockCode,
    Description,
    SUM(Quantity) AS Total_Quantity,
    SUM(Quantity * Price) AS Revenue
FROM retail
WHERE StockCode NOT IN ('POST', 'DOT', 'C2')
GROUP BY StockCode, Description
ORDER BY Total_Quantity DESC
LIMIT 10;

-- 3. Revenue by Country
SELECT
    Country,
    SUM(Quantity * Price) AS Revenue,
    COUNT(DISTINCT "Customer ID") AS Num_Customers
FROM retail
GROUP BY Country
ORDER BY Revenue DESC;

-- Average, median and largest order by month
WITH orders AS (
    SELECT
        Invoice,
        DATE_TRUNC('month', MIN(InvoiceDate)) AS Month,
        SUM(Quantity * Price) AS Order_Value
    FROM retail
    GROUP BY Invoice
)
SELECT
    Month,
    COUNT(*) AS Orders,
    ROUND(AVG(Order_Value), 2) AS Average_Order,
    ROUND(MEDIAN(Order_Value), 2) AS Median_Order,
    ROUND(MAX(Order_Value), 2) AS Largest_Order,
    ROUND((SUM(Order_Value) - MAX(Order_Value)) / (COUNT(*) - 1), 2) AS Average_Without_Largest
FROM orders
WHERE Month IN ('2010-11-01', '2010-12-01', '2011-01-01', '2011-11-01', '2011-12-01')
GROUP BY Month
ORDER BY Month;

-- Question 1: Is the business growing year over year?
WITH monthly AS (
    SELECT
        YEAR(InvoiceDate) AS Year,
        MONTH(InvoiceDate) AS Month,
        SUM(Quantity * Price) AS Revenue
    FROM retail
    GROUP BY Year, Month
)
SELECT
    Year,
    Month,
    ROUND(Revenue) AS Revenue,
    ROUND(SUM(Revenue) OVER (PARTITION BY Year ORDER BY Month)) AS Running_Total,
    ROUND((Revenue - LAG(Revenue, 12) OVER (ORDER BY Year, Month)) / LAG(Revenue, 12) OVER (ORDER BY Year, Month) * 100, 1) AS Change_From_Last_Year_Pct
FROM monthly
WHERE Year >= 2010
ORDER BY Year, Month;

-- Question 1: Is the business growing year over year?
SELECT
    YEAR(InvoiceDate) AS Year,
    ROUND(SUM(Quantity * Price)) AS Revenue_Jan_to_Nov
FROM retail
WHERE MONTH(InvoiceDate) <= 11
  AND YEAR(InvoiceDate) >= 2010
GROUP BY Year
ORDER BY Year;

-- Question 2: Do the best-selling products differ by country?
WITH product_sales AS (
    SELECT
        Country,
        StockCode,
        MAX(Description) AS Description,
        SUM(Quantity * Price) AS Revenue
    FROM retail
    WHERE StockCode NOT IN ('POST', 'DOT', 'C2')
    GROUP BY Country, StockCode
),
ranked AS (
    SELECT
        *,
        RANK() OVER (PARTITION BY Country ORDER BY Revenue DESC) AS Rank_In_Country
    FROM product_sales
)
SELECT
    Country,
    Rank_In_Country,
    Description,
    ROUND(Revenue) AS Revenue
FROM ranked
WHERE Rank_In_Country <= 3
  AND Country IN ('United Kingdom', 'EIRE', 'Netherlands', 'Germany', 'France')
ORDER BY Country, Rank_In_Country;

-- Question 3: How much of the business comes from returning customers?
WITH first_order AS (
    SELECT
        "Customer ID" AS Customer_ID,
        DATE_TRUNC('month', MIN(InvoiceDate)) AS First_Month
    FROM retail
    GROUP BY "Customer ID"
),
monthly_customers AS (
    SELECT DISTINCT
        "Customer ID" AS Customer_ID,
        DATE_TRUNC('month', InvoiceDate) AS Order_Month
    FROM retail
)
SELECT
    m.Order_Month,
    COUNT(*) AS Customers,
    SUM(CASE WHEN m.Order_Month = f.First_Month THEN 1 ELSE 0 END) AS New_Customers,
    SUM(CASE WHEN m.Order_Month > f.First_Month THEN 1 ELSE 0 END) AS Returning_Customers,
    ROUND(SUM(CASE WHEN m.Order_Month > f.First_Month THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS Pct_Returning
FROM monthly_customers AS m
JOIN first_order AS f
    ON m.Customer_ID = f.Customer_ID
GROUP BY m.Order_Month
ORDER BY m.Order_Month;

-- Question 3: How much of the business comes from returning customers?
WITH first_order AS (
    SELECT
        "Customer ID" AS Customer_ID,
        DATE_TRUNC('month', MIN(InvoiceDate)) AS First_Month
    FROM retail
    GROUP BY "Customer ID"
)
SELECT
    YEAR(r.InvoiceDate) AS Year,
    ROUND(SUM(CASE WHEN DATE_TRUNC('month', r.InvoiceDate) > f.First_Month THEN r.Quantity * r.Price ELSE 0 END) * 100.0
          / SUM(r.Quantity * r.Price), 1) AS Pct_Revenue_From_Returning
FROM retail AS r
JOIN first_order AS f
    ON r."Customer ID" = f.Customer_ID
WHERE YEAR(r.InvoiceDate) >= 2010
GROUP BY Year
ORDER BY Year;

-- Question 4: Do new customers come back?
WITH first_order AS (
    SELECT
        "Customer ID" AS Customer_ID,
        DATE_TRUNC('month', MIN(InvoiceDate)) AS First_Month
    FROM retail
    GROUP BY "Customer ID"
),
monthly_customers AS (
    SELECT DISTINCT
        "Customer ID" AS Customer_ID,
        DATE_TRUNC('month', InvoiceDate) AS Order_Month
    FROM retail
),
cohort_activity AS (
    SELECT
        f.First_Month,
        DATE_DIFF('month', f.First_Month, m.Order_Month) AS Months_Later,
        COUNT(DISTINCT m.Customer_ID) AS Customers
    FROM monthly_customers AS m
    JOIN first_order AS f
        ON m.Customer_ID = f.Customer_ID
    GROUP BY f.First_Month, Months_Later
)
SELECT
    First_Month,
    MAX(CASE WHEN Months_Later = 0 THEN Customers END) AS Cohort_Size,
    ROUND(MAX(CASE WHEN Months_Later = 1 THEN Customers END) * 100.0 / MAX(CASE WHEN Months_Later = 0 THEN Customers END), 1) AS Pct_Back_Month_1,
    ROUND(MAX(CASE WHEN Months_Later = 3 THEN Customers END) * 100.0 / MAX(CASE WHEN Months_Later = 0 THEN Customers END), 1) AS Pct_Back_Month_3,
    ROUND(MAX(CASE WHEN Months_Later = 6 THEN Customers END) * 100.0 / MAX(CASE WHEN Months_Later = 0 THEN Customers END), 1) AS Pct_Back_Month_6,
    ROUND(MAX(CASE WHEN Months_Later = 12 THEN Customers END) * 100.0 / MAX(CASE WHEN Months_Later = 0 THEN Customers END), 1) AS Pct_Back_Month_12
FROM cohort_activity
WHERE First_Month >= '2010-01-01'
  AND First_Month <= '2011-11-01'
GROUP BY First_Month
ORDER BY First_Month;

-- Question 4: share of new customers who ever came back
WITH customer_months AS (
    SELECT
        "Customer ID" AS Customer_ID,
        DATE_TRUNC('month', MIN(InvoiceDate)) AS First_Month,
        COUNT(DISTINCT DATE_TRUNC('month', InvoiceDate)) AS Months_With_Orders
    FROM retail
    GROUP BY "Customer ID"
)
SELECT
    COUNT(*) AS New_Customers_In_2010,
    SUM(CASE WHEN Months_With_Orders > 1 THEN 1 ELSE 0 END) AS Came_Back,
    ROUND(SUM(CASE WHEN Months_With_Orders > 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS Pct_Came_Back
FROM customer_months
WHERE First_Month >= '2010-01-01'
  AND First_Month <= '2010-12-01';

-- Question 5: How concentrated is revenue among customers?
WITH customer_totals AS (
    SELECT
        "Customer ID" AS Customer_ID,
        SUM(Quantity * Price) AS Revenue,
        COUNT(DISTINCT Invoice) AS Orders
    FROM retail
    GROUP BY "Customer ID"
),
grouped AS (
    SELECT
        *,
        NTILE(10) OVER (ORDER BY Revenue DESC) AS Spend_Group
    FROM customer_totals
)
SELECT
    Spend_Group,
    COUNT(*) AS Customers,
    ROUND(SUM(Revenue)) AS Revenue,
    ROUND(SUM(Revenue) * 100.0 / SUM(SUM(Revenue)) OVER (), 1) AS Pct_Of_Revenue,
    ROUND(AVG(Orders), 1) AS Average_Orders
FROM grouped
GROUP BY Spend_Group
ORDER BY Spend_Group;
