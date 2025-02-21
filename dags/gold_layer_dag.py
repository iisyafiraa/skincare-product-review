import os
import yaml
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'isyafira',
    'start_date': datetime(2025, 2, 13),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'catchup': False,
}

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
    'gold_layer_dag',
    default_args=default_args,
    description='Data Load to Gold Layer',
    schedule_interval=None,  # Trigger manually via external trigger
    max_active_runs=1,
    catchup=False,
    tags=['load']
) as dag:

    start_task = EmptyOperator(task_id='start_task')
    end_task = EmptyOperator(task_id='end_task')
    wait_create_task = EmptyOperator(task_id='wait_create_task')

    # Create table tasks
    create_dim_category_task = PythonOperator(
        task_id='create_dim_category',
        python_callable=execute_sql,
        op_args=['/opt/airflow/dags/resources/sql/gold/dim_category.sql'],
    )

    create_dim_product_task = PythonOperator(
        task_id='create_dim_product',
        python_callable=execute_sql,
        op_args=['/opt/airflow/dags/resources/sql/gold/dim_product.sql'],
    )

    create_dim_review_task = PythonOperator(
        task_id='create_dim_review',
        python_callable=execute_sql,
        op_args=['/opt/airflow/dags/resources/sql/gold/dim_review.sql'],
    )

    create_fact_product_review = PythonOperator(
        task_id='create_fact_product_review',
        python_callable=execute_sql,
        op_args=['/opt/airflow/dags/resources/sql/gold/fact_product_review.sql'],
    )

    # Defining the DAG structure
    start_task >> create_dim_category_task >> create_dim_product_task >> create_dim_review_task >> create_fact_product_review >> wait_create_task
    wait_create_task >> end_task
