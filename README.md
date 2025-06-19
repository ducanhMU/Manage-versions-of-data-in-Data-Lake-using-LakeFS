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
mc alias list                     # Kiểm tra alias
mc alias remove myminio          # Xóa alias (nếu sai)
mc mb myminio/mybucket           # Tạo bucket
mc ls myminio                    # Liệt kê bucket
mc ls myminio/mybucket           # Liệt kê file trong bucket
mc cp /data/file.csv myminio/mybucket # Upload file
```

> ✨ **Thư mục `/data` trong container `mc` đã được mount từ `data/` host.**

---

### 2.2. Dùng `lakectl` (CLI lakeFS)

```bash
docker compose exec -it lakefs sh   # Vào container lakefs
exit                                # Thoát
lakectl --help                      # Hướng dẫn
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

### \$ <img src="images/upload files.png" alt="upload files" width="600"/>

### Xoá file / thư mục:

```bash
lakectl fs rm lakefs://myrepo/main/students.csv
lakectl fs rm --recursive lakefs://myrepo/main/rawdata/
```

### Commit thay đổi:

```bash
lakectl commit lakefs://myrepo/dev -m "upd"
```

### \$ <img src="images/branch commit.png" alt="branch commit" width="600"/>

### Nhánh (branch):

```bash
lakectl branch create lakefs://myrepo/dev --source lakefs://myrepo/main
```

### \$ <img src="images/create new branch.png" alt="create new branch" width="600"/>

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
lakectl diff lakefs://myrepo/dev                        # Xem thay đổi của nhánh
lakectl merge lakefs://myrepo/dev lakefs://myrepo/main  # Merge vào main, source-dest
```

### \$ <img src="images/merge.png" alt="merge" width="600"/>

---

## 4. Kết nối Apache Spark

**Phụ thuộc:**

```bash
--packages org.apache.hadoop:hadoop-aws:3.3.2
```

**Thiết lập config:**

```bash
spark.hadoop.fs.s3a.access.key=admin
spark.hadoop.fs.s3a.secret.key=Admin12345
spark.hadoop.fs.s3a.endpoint=http://minio:9000
spark.hadoop.fs.s3a.path.style.access=true
spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem
```

---

## 5. Xử lý với Spark

**Đọc file:**

```python
spark.read.csv("s3a://mybucket/file.csv", header=True)
```

**Ghi kết quả:**

```python
df.write.csv("s3a://mybucket/processed/")
```

---

## 6. Delta Lake

**Phụ thuộc:**

```bash
--packages io.delta:delta-core_2.12:2.4.0
```

**Khởi tạo SparkSession:**

```python
spark = SparkSession.builder \
    .appName("DeltaLake Integration") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()
```

**Ghi và đọc:**

```python
df.write.format("delta").save("s3a://mybucket/delta-table")
delta_df = spark.read.format("delta").load("s3a://mybucket/delta-table")
```

**Time travel:**

```python
spark.read.format("delta").option("versionAsOf", 0).load("s3a://mybucket/delta-table")
```

---

## Cấu trúc dự án

```text
demo/
├── data/             # Dữ liệu upload
├── docker-compose.yml
├── .env              # Thông tin credentials
├── lakectl.yaml      # Cấu hình CLI lakectl
└── README.md         # File hướng dẫn
```
