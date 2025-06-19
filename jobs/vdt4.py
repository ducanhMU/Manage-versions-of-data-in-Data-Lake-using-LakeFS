# VDT'25 ML
# Chuyển dữ liệu log_app_test.csv sang định dạng Delta Lake để áp dụng tính năng như Time Travel, Vacuum
#--------------------------------------------
from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import *
from pyspark.sql.window import Window
from pyspark.ml.feature import StringIndexer
from functools import reduce
from delta.tables import DeltaTable
import os

# 1. Khởi tạo SparkSession với cấu hình cho lakeFS và Delta Lake
spark = SparkSession.builder\
    .appName("Delta Lake")\
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")\
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")\
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000")\
    .config("spark.hadoop.fs.s3a.path.style.access", "true")\
    .config("spark.hadoop.fs.s3a.access.key", os.getenv("MINIO_ROOT_USER"))\
    .config("spark.hadoop.fs.s3a.secret.key", os.getenv("MINIO_ROOT_PASSWORD"))\
    .config("spark.hadoop.fs.lakefs.impl", "io.lakefs.LakeFSFileSystem")\
    .config("spark.hadoop.fs.lakefs.endpoint", "http://lakefs:8000/api/v1")\
    .config("spark.hadoop.fs.lakefs.access.key", os.getenv("LAKEFS_ACCESS_KEY"))\
    .config("spark.hadoop.fs.lakefs.secret.key", os.getenv("LAKEFS_SECRET_KEY"))\
    .getOrCreate()

# 2. Đọc dữ liệu từ CSV (ban đầu chưa có ID và label)
df = spark.read\
    .option("header", True)\
    .option("inferSchema", False)\
    .csv("lakefs://myrepo/dev/rawdata/log_app_test.csv")

# 3. Ép kiểu các cột về Double
for c in df.columns:
    df = df.withColumn(c, col(c).cast(DoubleType()))

# 4. Ghi dữ liệu gốc sang định dạng Delta (version 0)
df.write.format("delta").mode("overwrite")\
    .save("lakefs://myrepo/dev/processed-data/delta/")

# 5. Đọc lại dữ liệu Delta version 0 để xử lý thêm feature
# (vẫn giữ nguyên dữ liệu ban đầu ở version 0)
df = spark.read.format("delta")\
    .load("lakefs://myrepo/dev/processed-data/delta/")

# 6. Bổ sung ID và label: ID là thứ tự tăng theo duration, label = 0 nếu duration <= 60
w = Window.orderBy(col('duration').asc())
df = df.withColumn('id', rank().over(w))\
         .withColumn('label', when(col('duration') <= 60, 0).otherwise(1))

# 7. Tạo feature fe1: trung bình các cột broadcast
bCols = [col(c) for c in df.columns if c.startswith('broadcast')]
if bCols:
    df = df.withColumn('fe1', reduce(lambda x, y: x + y, bCols) / len(bCols))

# 8. Tạo feature fe2: trung bình các cột cartesian
cCols = [col(c) for c in df.columns if c.startswith('cartesian')]
if cCols:
    df = df.withColumn('fe2', reduce(lambda x, y: x + y, cCols) / len(cCols))

# 9. fe3: StringIndexer từ cột sizeRelatedTable (chuyển về string trước)
df = df.withColumn('sizeRelatedTable_str', col('sizeRelatedTable').cast(StringType()))
indexer = StringIndexer(inputCol='sizeRelatedTable_str', outputCol='fe3')
df = indexer.fit(df).transform(df)

# 10. fe4: Phân loại tứ phân vị của duration
q1, q2, q3 = df.approxQuantile('duration', [0.25, 0.5, 0.75], 0.01)
df = df.withColumn('fe4', 
    when(col('duration') <= q1, 1)\
    .when(col('duration') <= q2, 2)\
    .when(col('duration') <= q3, 3)\
    .otherwise(4))

# 11. Ghi dữ liệu đã xử lý thành version mới (version 1)
df.write.format("delta").mode("overwrite")\
    .save("lakefs://myrepo/dev/processed-data/delta/")

# 12. Truy vấn lại version 0 (time travel)
df_v0 = spark.read.format("delta").option("versionAsOf", 0)\
    .load("lakefs://myrepo/dev/processed-data/delta/")

# 13. Thực hiện vacuum (soft delete các file không còn dùng)
delta_table = DeltaTable.forPath(spark, "lakefs://myrepo/dev/processed-data/delta/")
delta_table.vacuum()
