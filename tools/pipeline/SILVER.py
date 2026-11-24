# Databricks notebook source
# MAGIC %md
# MAGIC # SILVER: check, clean and type the data
# MAGIC
# MAGIC Takes the raw Bronze rows and:
# MAGIC
# MAGIC 1. Labels every row as valid or rejected, with the reason.
# MAGIC 2. Saves the valid rows with proper data types (numbers, dates) and a line amount.
# MAGIC 3. Saves the rejected rows in their own table, so nothing disappears without a record.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: label every row
# MAGIC
# MAGIC A row is rejected if it has no customer ID, belongs to a cancelled order (invoice starts with C), or uses a non-product code such as a manual adjustment or bank charge.

# COMMAND ----------

# MAGIC %sql
# MAGIC create or replace temporary view checked_rows as
# MAGIC select
# MAGIC     *,
# MAGIC     case
# MAGIC             when customer_id is null or trim(customer_id) = '' then 'missing customer id'
# MAGIC             when invoice like 'C%' then 'cancelled order'
# MAGIC             when stock_code in ('M', 'D', 'BANK CHARGES', 'ADJUST', 'AMAZONFEE', 'TEST001', 'CRUK') then 'non-product code'
# MAGIC             else 'valid'
# MAGIC         end as row_status
# MAGIC from procat.retail.bronze_order_lines;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: save the valid rows with proper types

# COMMAND ----------

# MAGIC %sql
# MAGIC create or replace table procat.retail.silver_order_lines as
# MAGIC select
# MAGIC     invoice,
# MAGIC     stock_code,
# MAGIC     description,
# MAGIC     try_cast(quantity as int) as quantity,
# MAGIC     try_cast(invoice_date as timestamp) as invoice_date,
# MAGIC     try_cast(price as decimal(12,3)) as price,
# MAGIC     cast(try_cast(customer_id as double) as int) as customer_id,
# MAGIC     country,
# MAGIC     try_cast(quantity as int) * try_cast(price as decimal(12,3)) as line_amount
# MAGIC from checked_rows
# MAGIC where row_status = 'valid';

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: save the rejected rows with the reason

# COMMAND ----------

# MAGIC %sql
# MAGIC create or replace table procat.retail.silver_rejected_lines as
# MAGIC select
# MAGIC     invoice,
# MAGIC     stock_code,
# MAGIC     description,
# MAGIC     quantity,
# MAGIC     invoice_date,
# MAGIC     price,
# MAGIC     customer_id,
# MAGIC     country,
# MAGIC     row_status as reject_reason
# MAGIC from checked_rows
# MAGIC where row_status <> 'valid';

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check 1: how many rows were rejected, and why

# COMMAND ----------

# MAGIC %sql
# MAGIC select
# MAGIC     reject_reason,
# MAGIC     count(*) as row_count
# MAGIC from procat.retail.silver_rejected_lines
# MAGIC group by reject_reason
# MAGIC order by row_count desc;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check 2: do the row counts add up?
# MAGIC
# MAGIC Bronze rows should equal Silver rows plus rejected rows. The last column should say true.

# COMMAND ----------

# MAGIC %sql
# MAGIC select
# MAGIC     b.bronze_rows,
# MAGIC     s.silver_rows,
# MAGIC     r.rejected_rows,
# MAGIC     b.bronze_rows = s.silver_rows + r.rejected_rows as counts_match
# MAGIC from (select count(*) as bronze_rows from procat.retail.bronze_order_lines) as b
# MAGIC cross join (select count(*) as silver_rows from procat.retail.silver_order_lines) as s
# MAGIC cross join (select count(*) as rejected_rows from procat.retail.silver_rejected_lines) as r;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check 3: quality of the Silver table
# MAGIC
# MAGIC No value should have failed to convert to a number or a date. Rows with a price of zero are kept (free items add no revenue) but counted here so they are visible.

# COMMAND ----------

# MAGIC %sql
# MAGIC select
# MAGIC     count(*) as silver_rows,
# MAGIC     count(distinct customer_id) as customers,
# MAGIC     count(distinct invoice) as orders,
# MAGIC     round(sum(line_amount), 2) as total_revenue,
# MAGIC     sum(case when quantity is null then 1 else 0 end) as bad_quantity,
# MAGIC     sum(case when price is null then 1 else 0 end) as bad_price,
# MAGIC     sum(case when invoice_date is null then 1 else 0 end) as bad_date,
# MAGIC     sum(case when price = 0 then 1 else 0 end) as zero_price_rows,
# MAGIC     min(invoice_date) as first_order,
# MAGIC     max(invoice_date) as last_order
# MAGIC from procat.retail.silver_order_lines;
