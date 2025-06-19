# VDT'25 coding test Q4
# Nội dung yêu cầu:

#     Lấy danh sách khóa học bạn đã đăng ký có tổng thời lượng học lớn nhất trên từng nền tảng
#     Sắp xếp theo theo tổng thời lượng học theo thứ tự giảm dần (desc), đơn vị giờ (h)
#     Schema bảng đầu ra gồm: full_name, email, course_title, platform, tot_duration, start_date, end_date
#     Định dạng trường date: yyyyMMdd

# Yêu cầu đầu ra:

#     Lưu file output với định dạng parquet
#     File output có tên 'result_p1_4'
#--------------------------------------------
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
result1 = df_students.join(df_learning_courses, df_students['student_id'] == df_learning_courses['student_id'])

temp_df = df_content_access_logs.groupBy('course_id').agg(sum('duration_sec').alias('time'))
temp_df = temp_df.withColumn('total_duration', col('time')/ 3600)
temp_df = temp_df.where(col('total_duration') >= 2.0).orderBy('total_duration')

result2 = temp_df.join(result1, temp_df['course_id'] == result1['course_id'])
result2 = result2.select('full_name', col('mail').alias('email'), 'course_title', 'platform', 'total_duration', 'start_date', 'end_date').orderBy('total_duration')

window = Window.partitionBy(['email', 'platform']).orderBy(col('total_duration').desc())
temp = result2.withColumn('rNum', row_number().over(window))
temp = temp.where(col('rNum') == 1)
temp = temp.orderBy(col('total_duration').desc())

result3 = temp.select('full_name', col('email'), 'course_title', 'platform', col('total_duration').alias('tot_duration'), 'start_date', 'end_date')

# ghi du lieu da xu ly ra thu muc processed-data cua nhanh dev
result3.write.format('parquet').mode('overwrite')\
    .save("lakefs://myrepo/dev/processed-data/result_p1_4.parquet")