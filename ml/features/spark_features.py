"""Batch feature aggregation example; requires pyspark in the Spark job environment."""
from pyspark.sql import Window
from pyspark.sql import functions as F


def transform_transactions(input_path: str, output_path: str) -> None:
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.appName("fraud-offline-feature-engineering").getOrCreate()
    tx = spark.read.option("header", True).option("inferSchema", True).csv(input_path)
    tx = tx.withColumn("timestamp", F.to_timestamp("timestamp"))
    customer_window = Window.partitionBy("customer_id").orderBy(F.col("timestamp").cast("long")).rowsBetween(-100, -1)
    enriched = (tx.withColumn("customer_previous_txn_count", F.count("transaction_id").over(customer_window))
                .withColumn("customer_previous_avg_amount", F.avg("amount").over(customer_window))
                .withColumn("amount_to_previous_avg", F.col("amount") / F.greatest(F.col("customer_previous_avg_amount"), F.lit(1.0))))
    enriched.write.mode("overwrite").parquet(output_path)
    spark.stop()
