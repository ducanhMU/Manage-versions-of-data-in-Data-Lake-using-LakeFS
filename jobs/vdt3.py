# VDT'25 coding test Q5
# Nội dung yêu cầu:

#     Lấy danh sách khóa học bạn đăng ký và xác định loại nội dung chủ yếu của khóa học đó là gì thông qua trường main_content. VD: khóa học có loại nội dung 'pdf' nhiều nhất => 'pdf', khóa học có loại nội dung 'video' nhiều nhất => 'video'
#     Sắp xếp theo nền tảng với thứ tự tăng dần (asc) và ngày bắt đầu khóa học với thứ tự giảm dần (desc) (nền tảng trước)
#     Schema bảng đầu ra gồm: course_title, platform, main_content, start_date, end_date
#     Định dạng trường date: yyyyMMdd

# Yêu cầu đầu ra:

#     Lưu file output với định dạng orc
#     File output có tên 'result_p1_5'
#-----------------------------------------
from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import *
from pyspark.sql.window import Window
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

df_content_access_logs = spark.read\
    .parquet("lakefs://myrepo/dev/rawdata/content_access_logs.parquet")

# xu ly du lieu

window = Window.partitionBy(['course_id', 'content_type'])
ttemp = df_content_access_logs.withColumn('cnt', count('*').over(window))

window = Window.partitionBy('course_id').orderBy(col('cnt').desc())
ttemp = ttemp.withColumn('rNum', row_number().over(window))
ttemp = ttemp.where(col('rNum') == 1)

# ttemp = ttemp.orderBy('platform', col('start_date').desc())
result4 = ttemp.join(df_learning_courses, ttemp['course_id'] == df_learning_courses['course_id'])
result4 = result4.orderBy(['platform', 'start_date'], ascending = [1, 0])
result4 = result4.select('course_title', 'platform', col('content_type').alias('main_content'), 'start_date', 'end_date')

# ghi du lieu da xu ly ra thu muc processed-data cua nhanh dev
result4.write.format('orc').mode('overwrite')\
    .save("lakefs://myrepo/dev/processed-data/result_p1_5.orc")

