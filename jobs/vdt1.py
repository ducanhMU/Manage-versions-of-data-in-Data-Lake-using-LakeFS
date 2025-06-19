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