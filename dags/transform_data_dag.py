import os
import psycopg2
import yaml
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.operators.dagrun_operator import TriggerDagRunOperator
from pyspark.sql import SparkSession
from datetime import datetime, timedelta
from pyspark.sql import functions as F
from pyspark.sql.functions import col, when, current_date, date_sub, regexp_extract, to_date

default_args = {
    'owner': 'isyafira',
    'start_date': datetime(2025, 2, 13),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'catchup': False,
}

# Inisialisasi Spark session
def init_spark():
    return SparkSession.builder \
        .appName("Data Transformation") \
        .config("spark.jars", "/opt/airflow/jars/postgresql-42.2.18.jar") \
        .config("spark.driver.extraClassPath", "/opt/airflow/jars/postgresql-42.2.18.jar") \
        .config("spark.executor.extraClassPath", "/opt/airflow/jars/postgresql-42.2.18.jar") \
        .config("spark.sql.catalogImplementation", "in-memory") \
        .getOrCreate()

# Fungsi untuk mengambil URL JDBC dari environment variable
def get_jdbc_url():
    # Mengambil URL JDBC dari environment variable
    jdbc_url = os.getenv('DATAENG_JDBC_POSTGRES_URI')
    if not jdbc_url:
        raise ValueError("DATAENG_JDBC_POSTGRES_URI environment variable is not set")
    return jdbc_url

# Fungsi untuk mengambil username dan password dari environment variable
def get_postgres_credentials():
    # Mengambil username dan password dari environment variable
    username = os.getenv('POSTGRES_USER')
    password = os.getenv('POSTGRES_PASSWORD')
    if not username or not password:
        raise ValueError("POSTGRES_USER or POSTGRES_PASSWORD environment variable is not set")
    return username, password

# Fungsi untuk melakukan transformasi kategori dengan PySpark
def transform_category_data(**kwargs):
    spark = init_spark()

    # Mengambil URL JDBC dari environment variable
    jdbc_url = get_jdbc_url()
    
    # Mengambil username dan password
    username, password = get_postgres_credentials()

    # Menambahkan username dan password ke dalam URL JDBC
    jdbc_url_with_credentials = jdbc_url + f"?user={username}&password={password}"

    # Membaca data kategori dari PostgreSQL menggunakan JDBC
    category_df = spark.read \
        .format("jdbc") \
        .option("url", jdbc_url_with_credentials) \
        .option("dbtable", "bronze.category") \
        .option("driver", "org.postgresql.Driver") \
        .load()

    # Transformasi: Mengisi kategori yang null dengan mengambil nama kategori dari URL href
    category_df = category_df.withColumn(
        "category_name",
        F.when(
            (F.col("category_name").isNull()) | (F.col("category_name") == ""),
            F.initcap(
                F.regexp_replace(
                    F.regexp_extract(F.col("category_url"), r'\/products\/[^\/]+\/([^\/?]+)', 1), 
                    r'(-\d+)$', ''  # Menghapus angka dan tanda hubung di akhir
                )
            )
        ).otherwise(F.col("category_name"))
    )

    category_df = category_df.dropDuplicates(["category_name", "category_url"])

    # Menyimpan hasil transformasi ke dalam tabel 'category_transformed'
    category_df.write \
        .format("jdbc") \
        .option("url", jdbc_url_with_credentials) \
        .option("dbtable", "silver.category_transformed") \
        .option("driver", "org.postgresql.Driver") \
        .mode("append") \
        .save()

    spark.stop()

# Fungsi untuk melakukan transformasi produk dengan PySpark
def transform_product_data(**kwargs):
    spark = init_spark()

    # Mengambil URL JDBC dari environment variable
    jdbc_url = get_jdbc_url()
    
    # Mengambil username dan password
    username, password = get_postgres_credentials()

    # Menambahkan username dan password ke dalam URL JDBC
    jdbc_url_with_credentials = jdbc_url + f"?user={username}&password={password}"

    # Membaca data produk dari PostgreSQL menggunakan JDBC
    product_df = spark.read \
        .format("jdbc") \
        .option("url", jdbc_url_with_credentials) \
        .option("dbtable", "bronze.product") \
        .option("driver", "org.postgresql.Driver") \
        .load()

    product_df = product_df.withColumn(
        "url_parts", F.split(F.col("product_url"), "/")
    )

    product_df.select("product_url", "url_parts").show(truncate=False)

    # Menambahkan kolom 'brand_name' dan 'product_name' dari bagian URL yang sudah dipisah
    product_df = product_df.withColumn(
        "brand_name", 
        F.when((F.col("brand_name").isNull()) | (F.col("brand_name") == ""), 
               F.upper(F.col("url_parts")[F.size(F.col("url_parts")) - 2]))
        .otherwise(F.col("brand_name"))
    )

    product_df = product_df.withColumn(
        "product_name", 
        F.when((F.col("product_name").isNull()) | (F.col("product_name") == ""),
               F.upper(F.col("url_parts")[F.size(F.col("url_parts")) - 1]))
        .otherwise(F.col("product_name"))
    )

    product_df = product_df.withColumn(
        "reviews", 
        F.regexp_extract(F.col("reviews"), r"\((\d+)\)", 1)  # Menghilangkan tanda kurung dan mempertahankan angka
    )

    product_df = product_df.withColumn(
        "price", 
        F.regexp_replace(F.col("price"), r"Rp\.\s?|[.]", "")  # Menghapus "Rp." dan titik
    )

    product_df = product_df.drop("url_parts")
    product_df = product_df.dropDuplicates(["brand_name","product_name","price","product_url"])

    product_df.show()

    # Menyimpan hasil transformasi ke dalam tabel 'product_transformed'
    product_df.write \
        .format("jdbc") \
        .option("url", jdbc_url_with_credentials) \
        .option("dbtable", "silver.product_transformed") \
        .option("driver", "org.postgresql.Driver") \
        .mode("append") \
        .save()

    spark.stop()

# Fungsi untuk melakukan transformasi review dengan PySpark
def transform_review_data(**kwargs):
    spark = init_spark()

    # Mengambil URL JDBC dari environment variable
    jdbc_url = get_jdbc_url()
    
    # Mengambil username dan password
    username, password = get_postgres_credentials()

    # Menambahkan username dan password ke dalam URL JDBC
    jdbc_url_with_credentials = jdbc_url + f"?user={username}&password={password}"

    # Membaca data review dari PostgreSQL menggunakan JDBC
    review_df = spark.read \
        .format("jdbc") \
        .option("url", jdbc_url_with_credentials) \
        .option("dbtable", "bronze.review") \
        .option("driver", "org.postgresql.Driver") \
        .load()

    # Reviewer description
    review_df = review_df.withColumn(
        "reviewer_description",
        F.trim(F.regexp_replace(F.col("reviewer_description"), r"^\s*,|\s*,\s*$", ""))
    )

    review_df = review_df.withColumn(
        "skin_type",
        F.when(F.col("reviewer_description").rlike(r"Combination"), "Combination")
        .when(F.col("reviewer_description").rlike(r"Dry"), "Dry")
        .when(F.col("reviewer_description").rlike(r"Oily"), "Oily")
        .when(F.col("reviewer_description").rlike(r"Normal"), "Normal")
        .otherwise("Unknown")
    )

    review_df = review_df.withColumn(
        "skin_tone",
        F.when(F.col("reviewer_description").rlike(r"Dark"), "Dark")
        .when(F.col("reviewer_description").rlike(r"Light"), "Light")
        .when(F.col("reviewer_description").rlike(r"Medium"), "Medium")
        .otherwise("Unknown")
    )

    review_df = review_df.withColumn(
        "undertone",
        F.when(F.col("reviewer_description").rlike(r"Neutral"), "Neutral")
        .when(F.col("reviewer_description").rlike(r"Warm"), "Warm")
        .when(F.col("reviewer_description").rlike(r"Cool"), "Cool")
        .otherwise("Unknown")
    )

    review_df = review_df.drop("reviewer_description")

    # thumb-up
    review_df = review_df.withColumn(
        "thumb", 
        F.when(F.col("thumb") == "thumb_up", 1).otherwise(0)
    )

    # Transformasi: Mengisi rating kosong dengan 0
    review_df = review_df.withColumn("rating", when(col("rating").isNull(), 0).otherwise(col("rating")))

    # Purchase point
    review_df = review_df.withColumn(
        "purchase_point", 
        F.when(F.col("purchase_point").rlike("(?i)FD Flash Sale"), "FD Flash Sale")
        .when(F.col("purchase_point").rlike("(?i)Borma"), "Borma")
        .when(F.col("purchase_point").rlike("(?i)Lazada"), "Lazada")
        .otherwise(F.col("purchase_point"))
    )

    # New column: purchase_category
    review_df = review_df.withColumn(
        "platform",
        F.when(F.col("purchase_point").rlike("(?i)Lazada|Bukalapak|Shopee|JD.id|Blibli.com"), "E-commerce")
        .when(F.col("purchase_point").rlike("(?i)Carrefour|Giant|Hypermart"), "Supermarket")
        .when(F.col("purchase_point").rlike("(?i)Brand Website|Official Brand Store"), "Official Website")
        .when(F.col("purchase_point").rlike("(?i)Beauty Fest|Azarine event|Female Daily Event"), "Event")
        .otherwise("Other")
    )

    review_df = review_df.withColumn(
        "review_date",
        when(
            col("review_date").rlike("a day ago"),  # menangani "a day ago"
            date_sub(current_date(), 1)
        ).when(
            col("review_date").rlike(r"(\d+) days ago"),  # menangani "X days ago"
            date_sub(current_date(), regexp_extract(col("review_date"), r"(\d+) days ago", 1).cast("int"))
        ).when(
            col("review_date").rlike(r"(\d+) hours ago"),  # menangani "X hours ago" (anggap ini hari ini)
            current_date()
        ).otherwise(
            # Jika review_date sudah berupa tanggal yang valid dalam format "dd MMM yyyy"
            to_date(col("review_date"), "dd MMM yyyy")
        )
    )

    # Menyimpan hasil transformasi ke dalam tabel 'review_transformed'
    review_df.write \
        .format("jdbc") \
        .option("url", jdbc_url_with_credentials) \
        .option("dbtable", "silver.review_transformed") \
        .option("driver", "org.postgresql.Driver") \
        .mode("append") \
        .save()

    spark.stop()

# Fungsi untuk mengeksekusi SQL dari file
def execute_sql(sql_file_path):
    # Membaca isi file SQL
    with open(sql_file_path, 'r') as file:
        sql_content = file.read()

    # Eksekusi SQL ke database PostgreSQL
    from airflow.providers.postgres.hooks.postgres import PostgresHook
    postgres_hook = PostgresHook(postgres_conn_id='dibimbing-dataeng-postgres-airflow')
    postgres_hook.run(sql_content)

# Membuat DAG untuk transformasi
with DAG(
    'transform_data_dag',
    default_args=default_args,
    description='Data Transformation DAG for Scraped Data',
    schedule_interval=None,  # Trigger manually via external trigger
    max_active_runs=1,
    catchup=False,
    tags=['transform']
) as dag:

    start_task = EmptyOperator(task_id='start_task')
    end_task = EmptyOperator(task_id='end_task')
    wait_create_task = EmptyOperator(task_id='wait_create_task')

    # Create table tasks
    create_category_table_task = PythonOperator(
        task_id='create_category_table',
        python_callable=execute_sql,
        op_args=['/opt/airflow/dags/resources/sql/silver/category_transformed.sql'],
    )

    create_product_table_task = PythonOperator(
        task_id='create_product_table',
        python_callable=execute_sql,
        op_args=['/opt/airflow/dags/resources/sql/silver/product_transformed.sql'],
    )

    create_review_table_task = PythonOperator(
        task_id='create_review_table',
        python_callable=execute_sql,
        op_args=['/opt/airflow/dags/resources/sql/silver/review_transformed.sql'],
    )

    transform_category_task = PythonOperator(
        task_id='transform_category',
        python_callable=transform_category_data,
        provide_context=True,
    )

    transform_product_task = PythonOperator(
        task_id='transform_product',
        python_callable=transform_product_data,
        provide_context=True,
    )

    transform_review_task = PythonOperator(
        task_id='transform_review',
        python_callable=transform_review_data,
        provide_context=True,
    )

    trigger_transform_dag = TriggerDagRunOperator(
        task_id='trigger_gold_layer_dag',
        trigger_dag_id='gold_layer_dag',  # Gantilah ini dengan ID DAG yang sesuai
        conf={},  # Pilih True jika Anda ingin menunggu DAG lain selesai
    )

    # Defining the DAG structure
    start_task >> create_category_table_task >> create_product_table_task >> create_review_table_task >> wait_create_task
    wait_create_task >> transform_category_task >> transform_product_task >> transform_review_task >> trigger_transform_dag >> end_task
