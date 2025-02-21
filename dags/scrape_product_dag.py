import yaml
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.dagrun_operator import TriggerDagRunOperator

from datetime import datetime, timedelta
from resources.scripts.scrape import initialize_driver, scrape_categories, scrape_products, scrape_reviews, connect_to_db, insert_category_data, insert_product_data, insert_review_data

default_args = {
    'owner': 'isyafira',
    'start_date': datetime(2025, 2, 13),
    'retries': 1, 
    'retry_delay': timedelta(minutes=5),
    'catchup': False,
}

# Fungsi untuk scraping kategori
def scrape_category_task_func(**kwargs):
    driver = initialize_driver()
    try:
        # Scrape kategori
        list_of_category, list_of_href = scrape_categories(driver)
        
        # Menyimpan hasil XCom (list_of_category dan list_of_href)
        kwargs['ti'].xcom_push(key='categories', value=(list_of_category, list_of_href))
        
        return list_of_category, list_of_href
    finally:
        driver.quit()

# Fungsi untuk scraping produk
def scrape_product_task_func(**kwargs):
    # Mengambil kategori dari XCom
    categories = kwargs['ti'].xcom_pull(task_ids='scrape_category', key='categories')
    list_of_category, list_of_href = categories  # Mendapatkan kategori

    driver = initialize_driver()
    try:
        # Scrape produk berdasarkan kategori
        list_of_product = scrape_products(driver, list_of_href)
    
        # Menyimpan hasil produk ke XCom
        kwargs['ti'].xcom_push(key='products', value=list_of_product)

        return list_of_product
    finally:
        driver.quit()

# Fungsi untuk scraping review
def scrape_review_task_func(**kwargs):
    # Mengambil produk dari XCom
    products = kwargs['ti'].xcom_pull(task_ids='scrape_product', key='products')

    driver = initialize_driver()
    try:
        # Scrape review produk
        list_of_review = scrape_reviews(driver, products)

        # Menyimpan hasil review ke XCom
        kwargs['ti'].xcom_push(key='reviews', value=list_of_review)

        return list_of_review
    finally:
        driver.quit()

# Fungsi untuk insert data kategori ke DB
def insert_category_task_func(**kwargs):
    categories = kwargs['ti'].xcom_pull(task_ids='scrape_category', key='categories')
    connection = connect_to_db()
    insert_category_data(categories, connection)
    connection.close()

# Fungsi untuk insert data produk ke DB
def insert_product_task_func(**kwargs):
    products = kwargs['ti'].xcom_pull(task_ids='scrape_product', key='products')
    connection = connect_to_db()
    insert_product_data(products, connection)
    connection.close()

# Fungsi untuk insert data review ke DB
def insert_review_task_func(**kwargs):
    reviews = kwargs['ti'].xcom_pull(task_ids='scrape_review', key='reviews')
    connection = connect_to_db()
    insert_review_data(reviews, connection)
    connection.close()

# Fungsi untuk mengeksekusi SQL dari file
def execute_sql(sql_file_path):
    # Membaca isi file SQL
    with open(sql_file_path, 'r') as file:
        sql_content = file.read()

    # Membuat koneksi menggunakan PostgresHook
    postgres_hook = PostgresHook(postgres_conn_id='dibimbing-dataeng-postgres-airflow')
    
    # Eksekusi SQL ke database PostgreSQL
    postgres_hook.run(sql_content)

# Membuat DAG
with DAG(
    'scrape_product_dag',
    default_args=default_args,
    description='Pipeline for Female Daily',
    schedule_interval='@daily',
    max_active_runs=1,
    catchup=False,
    tags=['daily']
) as dag:

    start_task = EmptyOperator(task_id='start_task')
    wait_create_task = EmptyOperator(task_id="wait_el_task")
    wait_transform_task = EmptyOperator(task_id="wait_transform_task")
    end_task = EmptyOperator(task_id="end_task")

    scrape_category_task = PythonOperator(
        task_id='scrape_category',
        python_callable=scrape_category_task_func,
        provide_context=True,
    )

    scrape_product_task = PythonOperator(
        task_id='scrape_product',
        python_callable=scrape_product_task_func,
        provide_context=True,
    )

    scrape_review_task = PythonOperator(
        task_id='scrape_review',
        python_callable=scrape_review_task_func,
        provide_context=True,
    )

    insert_category_task = PythonOperator(
        task_id='insert_category',
        python_callable=insert_category_task_func,
        provide_context=True,
    )

    insert_product_task = PythonOperator(
        task_id='insert_product',
        python_callable=insert_product_task_func,
        provide_context=True,
    )

    insert_review_task = PythonOperator(
        task_id='insert_review',
        python_callable=insert_review_task_func,
        provide_context=True,
    )

    # Create table tasks
    create_category_table_task = PythonOperator(
        task_id='create_category_table',
        python_callable=execute_sql,
        op_args=['/opt/airflow/dags/resources/sql/bronze/category.sql'],
    )

    create_product_table_task = PythonOperator(
        task_id='create_product_table',
        python_callable=execute_sql,
        op_args=['/opt/airflow/dags/resources/sql/bronze/product.sql'],
    )

    create_review_table_task = PythonOperator(
        task_id='create_review_table',
        python_callable=execute_sql,
        op_args=['/opt/airflow/dags/resources/sql/bronze/review.sql'],
    )

    trigger_transform_dag = TriggerDagRunOperator(
        task_id='trigger_transform_dag',
        trigger_dag_id='transform_data_dag',  # Gantilah ini dengan ID DAG yang sesuai
        conf={},  # Bisa diisi jika ada parameter yang perlu diteruskan ke DAG yang dipicu
        wait_for_completion=False,  # Pilih True jika Anda ingin menunggu DAG lain selesai
    )

    start_task >> create_category_table_task >> create_product_table_task >> create_review_table_task >> wait_create_task
    wait_create_task >> scrape_category_task >> scrape_product_task >> scrape_review_task
    scrape_review_task >> insert_category_task >> insert_product_task >> insert_review_task >> wait_transform_task
    wait_transform_task >> trigger_transform_dag >> end_task
