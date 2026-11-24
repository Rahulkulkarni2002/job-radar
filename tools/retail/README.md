# Online Retail Sales Performance Dashboard

## At a glance

- **Question:** how is revenue trending, which products, countries and customers drive it, and where can it grow?
- **Data:** 804,824 cleaned transactions from a UK online gift retailer, December 2009 to December 2011.
- **Currency:** the data is in pounds (£). £1 was worth about $1.57 on average over this period, so total revenue of £17.6M is about $27.6M.
- **How:** 15 SQL queries (joins, CTEs, window functions) in DuckDB, cross-checked in pandas, and a Tableau dashboard.
- **Main findings:**
  - Sales jump every September (+36% and +48%) and drop every January (-21% and -36%).
  - Underneath the seasons, revenue is flat: January to November 2011 was 0.4% above 2010.
  - 91% of 2011 revenue came from customers who had bought before.
  - 74% of new customers come back, but only 1 in 5 does so the next month.
  - The top 10% of customers bring in 64% of revenue.

## Live Dashboard
🔗 [View interactive dashboard on Tableau Public](https://public.tableau.com/app/profile/rahul.kulkarni6129/viz/dataanalystproject_17865305719790/OnlineRetailSalesPerformanceDashboard2009-2011)

![Dashboard Preview](dashboard_screenshot.jpeg)

## Dataset
[Online Retail II](https://www.kaggle.com/datasets/mashlyn/online-retail-ii-uci): 1,067,371 raw transaction rows. This project uses a cleaned version (804,824 transactions, 5,855 customers). The cleaning decisions (missing customer IDs, cancelled orders, administrative codes, a duplicate-row investigation) are in `cleaning_script.py`.

Two companion projects use the same data:

- [snowflake-databricks-medallion-pipeline](https://github.com/Rahulkulkarni2002/snowflake-databricks-medallion-pipeline): the same cleaning rebuilt as a SQL pipeline, with matching results.
- [customer-segmentation-retention-analysis](https://github.com/Rahulkulkarni2002/customer-segmentation-retention-analysis): customer segments built from this data.

## Method
Each number was built in SQL against the cleaned data, checked a second way where possible (for example, month-over-month growth is calculated in both SQL and pandas), and questioned before being trusted. Several first results led to more digging and a changed conclusion (see findings 4 and 5).

## Findings

### Part 1: sales, products and countries

**1. Strong, repeating seasonality.** Revenue climbs sharply every September (+35.5% in 2010, +47.8% in 2011) and drops every January (-21.4% and -35.6%). The same pattern in two separate years rules out a one-off cause.

**2. Revenue and volume tell different stories.** The top product by revenue (REGENCY CAKESTAND 3 TIER, about £11.50 a unit, £286K in total) is not in the top 10 by quantity. The top product by quantity (WORLD WAR 2 GLIDERS, 109,169 units) sells for about £0.23 a unit. A retailer needs both rankings.

**3. The UK drives volume, but not all of the value.** The UK has 90% of transaction rows but 83.3% of revenue. The gap comes from a few high-value accounts abroad: Ireland has just 3 customers, averaging £200,220 each, against a median customer spend of under £900.

**4. An average can be moved by one order.** The average order value looks high in both Decembers (£633 and £666, against a usual £430 to £540). December 2010 is real: the median order rises too. December 2011 is not: a single order of £168,470 on the last day of the data causes it. Without that order the average is £450. The median is the safer measure here.

**5. Small samples mislead.** Several countries' average order values rest on one or two orders (Lebanon: £1,693.88 from a single order). Countries with fewer than 20 orders are left out of the comparison.

### Part 2: customer questions, in SQL

**6. Revenue is flat year over year.** January to November 2011 brought in £7,767,253 against £7,732,972 in 2010, a rise of 0.4%. The seasonal peaks are large, but underneath them the business is not growing.

**7. The best sellers differ by country.** The cakestand leads in the UK, Ireland and Germany. In France and the Netherlands the leaders are children's items: night lights, snack boxes and lunch boxes.

**8. Returning customers are most of the business.** They brought in 81.7% of revenue in 2010 and 91.1% in 2011, while new customers per month fell from 250 to 440 in early 2010 to 100 to 220 in 2011. Caution: the data starts in December 2009, so some early "new" customers were probably existing ones.

**9. New customers come back, but slowly.** Of the customers who joined in 2010, 73.8% bought again in a later month. But only about 1 in 5 buys again the very next month (20.5%), and a year on about 1 in 6 is buying in any given month (16.7%). Customers return months apart.

**10. Revenue is concentrated.** The top 10% of customers (586 people) bring in 63.8% of revenue. The bottom half together bring in 6.5%.

**What this adds up to:** the business lives on repeat customers and is not growing. Existing customers keep coming back, but months apart, and fewer new ones are arriving. The clearest opportunities are bringing customers back sooner and winning more new ones.

## The SQL

All queries are in the notebook and collected in [`queries.sql`](queries.sql).

| Question | SQL used |
|---|---|
| Revenue by month, with growth from the month before | CTE, `DATE_TRUNC`, `LAG` |
| Top products by revenue and by quantity | `GROUP BY`, filtering out postage codes |
| Revenue and share by country | `COUNT(DISTINCT ...)`, calculated share |
| Average, median and largest order by month | CTE, `MEDIAN`, `MAX` |
| Is the business growing year over year? | `SUM() OVER (PARTITION BY ...)` running total, `LAG(..., 12)` |
| Top 3 products in each country | two CTEs, `RANK() OVER (PARTITION BY ...)` |
| New and returning customers by month | two CTEs, `JOIN`, `CASE WHEN` |
| Cohort retention | three CTEs, `JOIN`, `DATE_DIFF`, `CASE WHEN` pivot |
| Revenue by customer spend group | CTE, `NTILE(10)`, `SUM() OVER ()` |

## Data quality notes

- **Incomplete final month.** The data ends on 2011-12-09, so December 2011 has 9 days. It is left out of trend and growth calculations, and this is stated on the dashboard.
- **Very large single orders.** Two orders (£168,470 and £77,184) are far larger than any others and distort monthly averages. They are kept in the totals and pointed out where they matter.
- **Revenue is gross.** Cancelled invoices are removed in cleaning, but an order that was later cancelled still counts at its original value.

## Files
- `sales_kpi_analysis.ipynb`: the full analysis, with notes on every finding
- `queries.sql`: the 15 SQL queries on their own
- `cleaning_script.py`: the data cleaning logic
- `monthly_revenue.csv`, `top_products_revenue.csv`, `top_products_quantity.csv`, `country_revenue.csv`, `aov_by_country.csv`: the tables behind the dashboard
- `requirements.txt`: the Python packages needed

## How to Reproduce
1. Clone this repo and run `pip install -r requirements.txt`.
2. Download the [Online Retail II dataset](https://www.kaggle.com/datasets/mashlyn/online-retail-ii-uci) and place it in the project folder as `online_retail_II.csv`.
3. Run `cleaning_script.py` to produce `cleaned_retail.csv`.
4. Open `sales_kpi_analysis.ipynb` and run all cells.
5. Open the exported CSVs in Tableau Public to rebuild the dashboard.

## Tools
SQL (DuckDB), Python (pandas), Tableau Public.
