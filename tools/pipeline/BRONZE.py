# Databricks notebook source
# MAGIC %md
# MAGIC # BRONZE: load the raw data from Snowflake
# MAGIC
# MAGIC Reads the raw retail transactions from Snowflake and saves them, unchanged, as a Delta table.
# MAGIC
# MAGIC Nothing is cleaned here. Every column stays as text, exactly as it arrived. Cleaning happens in the Silver layer.

# COMMAND ----------

# MAGIC %sql
# MAGIC create schema if not exists procat.retail;

# COMMAND ----------

# MAGIC %md
# MAGIC The Snowflake address, user and private key are stored in a Databricks secret scope, so no login details appear in this code.

# COMMAND ----------

sf_url = dbutils.secrets.get(scope="my-snowflake", key="url")
sf_user = dbutils.secrets.get(scope="my-snowflake", key="user")
sf_key = dbutils.secrets.get(scope="my-snowflake", key="private-key")

raw = (
    spark.read.format("snowflake")
    .option("sfUrl", sf_url)
    .option("sfUser", sf_user)
    .option("pem_private_key", sf_key)
    .option("sfDatabase", "RETAIL_DB")
    .option("sfSchema", "RAW")
    .option("sfWarehouse", "COMPUTE_WH")
    .option("dbtable", "ONLINE_RETAIL_RAW")
    .load()
)

# COMMAND ----------

# MAGIC %md
# MAGIC Snowflake returns column names in capitals. Make them lowercase, and add a column recording when the data was loaded.

# COMMAND ----------

from pyspark.sql.functions import current_timestamp

lowercase_names = [name.lower() for name in raw.columns]
bronze = raw.toDF(*lowercase_names)

bronze = bronze.withColumn("loaded_at", current_timestamp())

bronze.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("procat.retail.bronze_order_lines")

# COMMAND ----------

# MAGIC %md
# MAGIC **Check:** the Bronze table should have the same number of rows as the Snowflake table (1,067,371).

# COMMAND ----------

# MAGIC %sql
# MAGIC select count(*) as bronze_rows from procat.retail.bronze_order_lines;

# COMMAND ----------

# MAGIC %sql
# MAGIC select * from procat.retail.bronze_order_lines limit 10;
