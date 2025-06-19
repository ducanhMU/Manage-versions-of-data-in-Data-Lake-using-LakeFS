# Hướng dẫn khởi động và tương tác hệ thống

## 1. Khởi động hệ thống cơ bản

**Thành phần:**

* **lakeFS**: Quản lý phiên bản dữ liệu
* **PostgreSQL**: Lưu metadata cho lakeFS
* **MinIO**: Object store tương thích S3

**Bước thực hiện:**

```bash
sudo systemctl stop postgresql  # Tắt PostgreSQL nếu đang chiếm cổng 5432
docker compose up -d           # Khởi chạy các container
```

---

## 2. Tương tác qua CLI

### 2.1. Dùng `mc` (MinIO Client)

```bash
docker compose exec -it mc sh  # Vào container mc
exit                            # Thoát
```

**Thêm alias:**

```bash
mc alias set myminio http://minio:9000 admin Admin12345
```

**Lệnh cơ bản:**

```bash
mc alias list                               # Kiểm tra alias
mc alias remove myminio                    # Xóa alias (nếu sai)
mc mb myminio/mybucket                     # Tạo bucket
mc ls myminio                              # Liệt kê bucket
mc ls myminio/mybucket                     # Liệt kê file trong bucket
mc cp /data/file.csv myminio/mybucket      # Upload file
```

> ✨ **Thư mục `/data` trong container `mc` đã được mount từ `data/` host.**

---

### 2.2. Dùng `lakectl` (CLI lakeFS)

```bash
docker compose exec -it lakefs sh   # Vào container lakefs
lakectl --help                      # Hướng dẫn
exit                                # Thoát
```

> 🔹 File `lakectl.yaml` đã được mount sẵn, không cần đặt tay config.

---

## 3. Tương tác với lakeFS

### Tạo repo:

```bash
lakectl repo create lakefs://myrepo s3://mybucket
```

### Xóa repo:

```bash
lakectl repo delete lakefs://myrepo
```

### Xem dữ liệu trong nhánh:

```bash
lakectl fs ls lakefs://myrepo/main/
```

### Upload file:

```bash
lakectl fs upload --source /upload/students.csv lakefs://myrepo/main/students.csv
```

### Upload cả folder:

```bash
lakectl fs upload --recursive --source /upload/ lakefs://myrepo/main/rawdata/
```
<img src="images/upload files.png" width="700"/>

### Xóa file / thư mục:

```bash
lakectl fs rm lakefs://myrepo/main/students.csv
lakectl fs rm --recursive lakefs://myrepo/main/rawdata/
```

### Commit thay đổi:

```bash
lakectl commit lakefs://myrepo/dev -m "upd"
```
<img src="images/branch commit.png" width="700"/>

### Nhánh (branch):

```bash
lakectl branch create lakefs://myrepo/dev --source lakefs://myrepo/main
```
<img src="images/create new branch.png" width="700"/>

### Tạo thư mục bằng upload file:

```bash
echo "ghi chu" > issue.txt
lakectl fs upload --source issue.txt lakefs://myrepo/dev/processed-data/issue.txt
```

### Reset thay đổi chưa commit:

```bash
lakectl branch reset lakefs://myrepo/dev
```

### Rollback commit:

```bash
lakectl branch revert lakefs://myrepo/main <commit-id>
```

### Kiểm tra commit hiện tại:

```bash
lakectl branch show lakefs://myrepo/main
```

### So sánh và merge:

```bash
lakectl diff lakefs://myrepo/dev
lakectl merge lakefs://myrepo/dev lakefs://myrepo/main
```
<img src="images/merge.png" width="700"/>

---

## 4. Kết nối Apache Spark

Spark đọc ghi dữ liệu từ lakeFS thông qua connector `hadoop-lakefs`, tương thích với giao thức `lakefs://`.

> ✅ Tất cả cấu hình đã được đặt trong `docker-compose.yml`

### 🔧 Cấu hình quan trọng:

**Data plane (`s3a://`) – đi qua MinIO:**

```env
fs.s3a.endpoint=http://minio:9000
fs.s3a.path.style.access=true
fs.s3a.access.key=${MINIO_ROOT_USER}
fs.s3a.secret.key=${MINIO_ROOT_PASSWORD}
fs.s3a.connection.ssl.enabled=false
```

**Metadata plane (`lakefs://`) – xử lý version:**

```env
fs.lakefs.impl=io.lakefs.LakeFSFileSystem
fs.lakefs.endpoint=http://lakefs:8000/api/v1
fs.lakefs.access.key=${LAKEFS_ACCESS_KEY}
fs.lakefs.secret.key=${LAKEFS_SECRET_KEY}
```

### 📁 Mount thư viện và jobs:

* `./jobs:/opt/bitnami/spark/jobs:ro`: mount script xử lý như `vdt1.py`, `vdt2.py`, `vdt3.py`
* `./jars/io-lakefs-hadoop-lakefs-assembly-0.2.5.jar`: connector hỗ trợ `lakefs://`

---

## 5. Xử lý với Spark

### 🧪 Ví dụ: `jobs/vdt1.py`

```python
# VDT'25 coding test Q1
# Nội dung yêu cầu:

#     Lấy danh sách khóa học bạn đăng ký tham gia (theo tên hoặc email)
#     Schema bảng đầu ra gồm: full_name, mail, course_title, platform, start_date, end_date
#     Định dạng trường date: yyyyMMdd

# Yêu cầu đầu ra:

#     Lưu file output với định dạng csv không có header, phân cách trường bằng dấu phẩy ( , )
#     File output có tên 'result_p1_1'
#--------------------------------------------
from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import *
import os

# khoi tao SparkSession
spark = SparkSession.builder\
        .appName("lakeFS pySpark processing")\
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000")\
        .config("spark.hadoop.fs.s3a.path.style.access", "true")\
        .config("spark.hadoop.fs.s3a.access.key", os.getenv("MINIO_ROOT_USER"))\
        .config("spark.hadoop.fs.s3a.secret.key", os.getenv("MINIO_ROOT_PASSWORD"))\
        .config("spark.hadoop.fs.lakefs.impl", "io.lakefs.LakeFSFileSystem")\
        .config("spark.hadoop.fs.lakefs.endpoint", "http://lakefs:8000/api/v1")\
        .config("spark.hadoop.fs.lakefs.access.key", os.getenv("LAKEFS_ACCESS_KEY"))\
        .config("spark.hadoop.fs.lakefs.secret.key", os.getenv("LAKEFS_SECRET_KEY"))\
        .getOrCreate()

# doc du lieu tho tu thu muc rawdata cua nhanh dev
df_students = spark.read\
                .option("header", True)\
                .option("inferSchema", True)\
                .csv("lakefs://myrepo/dev/rawdata/students.csv")

df_learning_courses = spark.read\
                .orc("lakefs://myrepo/dev/rawdata/learning_courses.orc")

# xu ly du lieu
result1 = df_students.join(df_learning_courses, df_students['student_id'] == df_learning_courses['student_id'])
result1 = result1.select('full_name', 'mail', 'course_title', 'platform', 'start_date', 'end_date')

# ghi du lieu da xu ly ra thu muc processed-data cua nhanh dev
result1.write.mode('overwrite')\
    .format('csv').option('header', False)\
    .save("lakefs://myrepo/dev/processed-data/result_p1_1.csv")
```

### ⚙️ Chạy job:

```bash
docker compose exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  --packages io.lakefs:hadoop-lakefs-assembly:0.2.5 \
  /opt/bitnami/spark/jobs/vdt1.py
```
<img src="images/spark.png" width="700"/>

> ✨ Tương tự với `jobs/vdt2.py`, `jobs/vdt3.py` nếu có logic khác (ví dụ aggregate, join, etc.)

---

## 6. Delta Lake

Spark hỗ trợ Delta format nếu thêm thư viện tương ứng:

### Phụ thuộc:

```bash
--packages io.delta:delta-core_2.12:2.1.0
```
### 🧪 Ví dụ thao tác delta lake: `jobs/vdt4.py`
```python
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
```

### ⚙️ Chạy job:
```bash
docker compose exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  --packages io.delta:delta-core_2.12:2.1.0,io.lakefs:hadoop-lakefs-assembly:0.2.5 \
  /opt/bitnami/spark/jobs/vdt4.py
```

<img src="images/delta.png" width="700"/>
---

## Cấu trúc dự án

```text
demo/
├── data/               # Dữ liệu upload
├── docker-compose.yml
├── .env                # Thông tin credentials
├── lakectl.yaml        # Cấu hình CLI lakectl
├── jobs/               # Thư mục chứa file xử lý Spark
│   ├── vdt1.py
|   ├── vdt2.py
|   ├── vdt3.py
│   └── vdt4.py
├── images/             # Ảnh minh hoạ
└── README.md           # Hướng dẫn hệ thống
```

---