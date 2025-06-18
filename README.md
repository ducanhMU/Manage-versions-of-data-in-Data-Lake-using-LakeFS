# Hướng dẫn khởi động và tương tác hệ thống LakeFS + MinIO + PostgreSQL

## 1. Khởi động hệ thống cơ bản

**Thành phần:**

* **lakeFS** – Lớp quản lý version dữ liệu
* **PostgreSQL** – Lưu metadata cho lakeFS
* **MinIO** – Object store tương thích S3

**Bước thực hiện:**

* Tắt tiến trình PostgreSQL đang chiếm cổng `5432` nếu có:

  ```bash
  sudo systemctl stop postgresql
  ```

* Khởi chạy hệ thống bằng Docker Compose:

  ```bash
  docker compose up -d
  ```

---

## 2. Kết nối và tương tác qua CLI

### 2.1. Dùng `mc` (MinIO Client)

**Thao tác:**

* Truy cập container `mc`:

  ```bash
  docker compose exec -it mc sh
  ```

* Thoát:

  ```bash
  exit
  ```

**Cài đặt kết nối tới MinIO:**

```bash
mc alias set myminio http://minio:9000 admin Admin12345
```

**Một số lệnh thường dùng:**

* Liệt kê các bucket:

  ```bash
  mc ls myminio
  ```

* Tạo bucket mới:

  ```bash
  mc mb myminio/mybucket
  ```

* Upload dữ liệu từ thư mục `/data` trong container `mc` lên MinIO:

  ```bash
  mc cp /data/file.csv myminio/mybucket
  ```

> 📌 *Lưu ý:* Thư mục `/data` đã được mount từ thư mục `data/` ở máy host, nơi bạn để các file cần upload.

---

### 2.2. Dùng `lakectl` (CLI của lakeFS)

**Thao tác:**

* Truy cập container `lakefs`:

  ```bash
  docker compose exec -it lakefs sh
  ```

* Thoát:

  ```bash
  exit
  ```

**Ghi chú:**

* Container `lakefs` đã cài sẵn `lakectl`.
* File `lakectl.yaml` đã được mount vào `/home/lakefs/.lakectl.yaml`, chứa sẵn `access_key_id`, `secret_access_key` và `endpoint_url`, nên `lakectl` sẽ tự động kết nối khi sử dụng.

---

## 3. Tương tác với hệ thống lakeFS

### Tạo repository mới:

```bash
lakectl repo create lakefs://myrepo s3://mybucket
```

### Tạo nhánh (branch):

```bash
lakectl branch create lakefs://myrepo@dev --source main
```

### Upload dữ liệu:

(Sử dụng `mc` như hướng dẫn ở mục 2.1)

### Biến đổi dữ liệu (transform) và thao tác Git-like:

* Kiểm tra sự khác biệt:

  ```bash
  lakectl diff lakefs://myrepo@dev
  ```

* Commit:

  ```bash
  lakectl commit lakefs://myrepo@dev -m "My update"
  ```

* Merge vào nhánh chính:

  ```bash
  lakectl merge lakefs://myrepo@dev --destination lakefs://myrepo@main
  ```

* Rollback nếu cần:

  ```bash
  lakectl reset lakefs://myrepo@dev
  ```

* Tạo nhánh mới để thử nghiệm thêm:

  ```bash
  lakectl branch create lakefs://myrepo@experiment --source main
  ```

* Có thể cấu hình hook pre-merge, post-commit,... tùy nhu cầu.

---

## 4. Kết nối với Apache Spark

> (Hướng dẫn sẽ cập nhật khi Spark được tích hợp)

---

## 5. Xử lý dữ liệu với Spark

> (Hướng dẫn xử lý ETL, MLlib với Spark)

---

## 6. Kết nối với Delta Lake

> (Hướng dẫn cấu hình Spark để sử dụng Delta Lake kết hợp lakeFS)

---

## 7. Thao tác với Delta Lake

> (Tạo bảng Delta, ghi/đọc dữ liệu có version, time travel...)

---

## Cấu trúc thư mục dự án

```text
demo/
├── data/             # Thư mục chứa dữ liệu upload
├── docker-compose.yml
├── .env              # Chứa các biến môi trường như credentials
├── lakectl.yaml      # File cấu hình cho lakectl
└── README.md         # (file này)
```