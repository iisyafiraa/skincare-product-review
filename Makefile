include .env

help:
	@echo "## docker-build				- Build Docker Images (amd64) including its inter-container network."
	@echo "## postgres					- Run a Postgres container debezium ready."
	@echo "## spark						- Run a Spark cluster, rebuild the postgres container, then create the destination tables "
	@echo "## airflow					- Spinup airflow scheduler and webserver."
	@echo "## metabase					- Run a Metabase container to visualize."

# Building the docker images for arm-based machines
docker-build:
	@echo '__________________________________________________________'
	@echo 'Building Docker Images ...'
	@echo '__________________________________________________________'
	@docker network inspect finpro-network >/dev/null 2>&1 || docker network create finpro-network
	@echo '__________________________________________________________'
	@docker build --no-cache -t dataeng-dibimbing/airflow -f ./docker/Dockerfile.airflow .
	@echo '==========================================================='
	@docker build --no-cache -t dataeng-dibimbing/jupyter -f ./docker/Dockerfile.jupyter .
	@echo '==========================================================='
	@docker build --no-cache -t dataeng-dibimbing/superset -f ./docker/Dockerfile.superset .
	@echo '==========================================================='

# Creating the airflow instance
airflow: airflow-create
airflow-create:
	@echo '__________________________________________________________'
	@echo 'Creating Airflow Instance ...'
	@echo '__________________________________________________________'
	@docker compose -f ./docker/docker-compose-airflow.yml --env-file .env up -d
	@echo 'Access webserver at at http://localhost:${AIRFLOW_WEBSERVER_PORT} ...'
	@echo '==========================================================='

# Creating the postgres instance
postgres: postgres-create
postgres-create:
	@docker compose -f ./docker/docker-compose-postgres.yml --env-file .env up -d
	@echo '__________________________________________________________'
	@echo 'Main Postgres container created at port ${POSTGRES_PORT}...'
	@echo '__________________________________________________________'
	@echo 'Main Postgres Docker Host	: ${POSTGRES_CONTAINER_NAME}' &&\
		echo 'Main Postgres Account	: ${POSTGRES_USER}' &&\
		echo 'Main Postgres password	: ${POSTGRES_PASSWORD}' &&\
		echo 'Main Postgres Db		: ${POSTGRES_DB}'
	@echo '__________________________________________________________'
	@echo 'Replica Postgres container created at port ${POSTGRES_REPLICA_PORT}...'
	@echo '__________________________________________________________'
	@echo 'Replica Postgres Docker Host	: ${POSTGRES_REPLICA_CONTAINER_NAME}' &&\
		echo 'Replica Postgres Account	: ${POSTGRES_REPLICA_USER}' &&\
		echo 'Replica Postgres password	: ${POSTGRES_REPLICA_PASSWORD}' &&\
		echo 'Replica Postgres Db		: ${POSTGRES_REPLICA_DB}'
	@echo '__________________________________________________________'
	@echo 'Source Postgres Host	: ${POSTGRES_HOST_SOURCE}' &&\
		echo 'Source Postgres Account	: ${POSTGRES_SOURCE_USER}' &&\
		echo 'Source Postgres password	: ${POSTGRES_SOURCE_PASSWORD}' &&\
		echo 'Source Postgres Db		: ${POSTGRES_SOURCE_DB}'
	@sleep 5
	@echo '==========================================================='

spark: spark-create
spark-create:
	@echo '__________________________________________________________'
	@echo 'Creating Spark Cluster ...'
	@echo '__________________________________________________________'
	@docker compose -f ./docker/docker-compose-spark.yml --env-file .env up -d
	@echo '==========================================================='

superset: superset-create
superset-create:
	@docker-compose -f ./docker/docker-compose-superset.yml -f ./docker/docker-compose-postgres.yml --env-file .env up -d
	@echo 'Access Superset at http://localhost:8088 ...'
	@echo '==========================================================='

postgres-create-warehouse:
	@echo '__________________________________________________________'
	@echo 'Creating Warehouse DB...'
	@echo '_________________________________________'
	@docker exec -it ${POSTGRES_CONTAINER_NAME} psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -f sql_external/warehouse-setup.sql
	@echo '==========================================================='

metabase: postgres-create-warehouse
	@echo '__________________________________________________________'
	@echo 'Creating Metabase Instance ...'
	@echo '__________________________________________________________'
	@docker compose -f ./docker/docker-compose-metabase.yml --env-file .env up
	@echo '==========================================================='

all:
	@make postgres
	@make airflow
	@make spark
	@make metabase

# Connecting to postgres container
postgres-bash:
	@docker exec -it dataeng-postgres bash

give-all-permission:
	@chmod +x scripts/entrypoint.sh
	@chmod -R 777 scripts
	@chmod -R 777 dags
	@chmod -R 777 dags/scrape_product_dag.py
	@chmod -R 777 data
	@chmod -R 777 jars
	@chmod -R 777 logs
	@chmod -R 777 spark_scripts
	@chmod -R 777 sql
	@echo '__________________________________________________________'
	@echo 'All permissions given'
	@echo '__________________________________________________________'