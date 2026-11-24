# Databricks notebook source
# MAGIC %md
# MAGIC # GOLD: summary tables for reporting
# MAGIC
# MAGIC Builds three small tables from the clean Silver data. These are the tables a sales dashboard reads:
# MAGIC
# MAGIC 1. Revenue by month, with growth from the month before.
# MAGIC 2. Sales by product, ranked by revenue and by units sold.
# MAGIC 3. Sales by country, with each country's share of revenue.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Table 1: revenue by month
# MAGIC
# MAGIC `LAG` looks up the revenue of the month before, so growth can be calculated. December 2011 only has 9 days of data, so it is flagged as a partial month.

# COMMAND ----------

# MAGIC %sql
# MAGIC create or replace table procat.retail.gold_monthly_revenue as
# MAGIC with monthly as (
# MAGIC     select
# MAGIC         cast(date_trunc('MONTH', invoice_date) as date) as order_month,
# MAGIC         sum(line_amount) as revenue,
# MAGIC         count(distinct invoice) as orders,
# MAGIC         count(distinct customer_id) as customers
# MAGIC     from procat.retail.silver_order_lines
# MAGIC     group by cast(date_trunc('MONTH', invoice_date) as date)
# MAGIC )
# MAGIC select
# MAGIC     order_month,
# MAGIC     round(revenue, 2) as revenue,
# MAGIC     orders,
# MAGIC     customers,
# MAGIC     round(revenue / orders, 2) as avg_order_value,
# MAGIC     round((revenue - lag(revenue) over (order by order_month)) / lag(revenue) over (order by order_month) * 100, 1) as growth_pct,
# MAGIC     order_month = date '2011-12-01' as is_partial_month
# MAGIC from monthly;

# COMMAND ----------

# MAGIC %sql
# MAGIC select * from procat.retail.gold_monthly_revenue order by order_month;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Table 2: sales by product
# MAGIC
# MAGIC Postage and carriage codes (POST, DOT, C2) are left out, because they are fees and not products. `RANK` gives each product its position by revenue and by units sold.

# COMMAND ----------

# MAGIC %sql
# MAGIC create or replace table procat.retail.gold_product_sales as
# MAGIC with products as (
# MAGIC     select
# MAGIC         stock_code,
# MAGIC         description,
# MAGIC         sum(line_amount) as revenue,
# MAGIC         sum(quantity) as units_sold
# MAGIC     from procat.retail.silver_order_lines
# MAGIC     where stock_code not in ('POST', 'DOT', 'C2')
# MAGIC     group by stock_code, description
# MAGIC )
# MAGIC select
# MAGIC     stock_code,
# MAGIC     description,
# MAGIC     round(revenue, 2) as revenue,
# MAGIC     units_sold,
# MAGIC     rank() over (order by revenue desc) as revenue_rank,
# MAGIC     rank() over (order by units_sold desc) as units_rank
# MAGIC from products;

# COMMAND ----------

# MAGIC %sql
# MAGIC select * from procat.retail.gold_product_sales where revenue_rank <= 10 order by revenue_rank;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Table 3: sales by country
# MAGIC
# MAGIC `SUM(...) OVER ()` gives the total across all countries, so each country's share can be calculated in the same query.

# COMMAND ----------

# MAGIC %sql
# MAGIC create or replace table procat.retail.gold_country_sales as
# MAGIC select
# MAGIC     country,
# MAGIC     round(sum(line_amount), 2) as revenue,
# MAGIC     count(distinct customer_id) as customers,
# MAGIC     count(distinct invoice) as orders,
# MAGIC     round(sum(line_amount) / count(distinct invoice), 2) as avg_order_value,
# MAGIC     round(sum(line_amount) / sum(sum(line_amount)) over () * 100, 2) as pct_of_revenue
# MAGIC from procat.retail.silver_order_lines
# MAGIC group by country;

# COMMAND ----------

# MAGIC %sql
# MAGIC select * from procat.retail.gold_country_sales order by revenue desc limit 10;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Final check: the whole pipeline in one table

# COMMAND ----------

# MAGIC %sql
# MAGIC select 'bronze_order_lines' as table_name, count(*) as row_count from procat.retail.bronze_order_lines
# MAGIC union all
# MAGIC select 'silver_order_lines', count(*) from procat.retail.silver_order_lines
# MAGIC union all
# MAGIC select 'silver_rejected_lines', count(*) from procat.retail.silver_rejected_lines
# MAGIC union all
# MAGIC select 'gold_monthly_revenue', count(*) from procat.retail.gold_monthly_revenue
# MAGIC union all
# MAGIC select 'gold_product_sales', count(*) from procat.retail.gold_product_sales
# MAGIC union all
# MAGIC select 'gold_country_sales', count(*) from procat.retail.gold_country_sales;
