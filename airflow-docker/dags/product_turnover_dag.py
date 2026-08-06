from datetime import datetime
import pandas as pd
from airflow.sdk import dag, task   # для airflow 3.0 вместо decorator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.empty import EmptyOperator

# Функция-заглушка для оповещения об ошибки
def notify_failure(context):
    # Сообщение об ошибке при падении любой задачи в DAG'е
    task_instance = context.get("task_instance")    # достанет из словаря contex airflow задачу update_datamart()
    exception = context.get("exception")    # достанет из словаря объект исключения, кот. описан в check_datamart()
    error_message = (
        f"Ошибка DAG '{task_instance.dag_id}' — задача '{task_instance.task_id}' упала.\n"
        f"Причина: {exception}"
    )
    print(error_message)  # сообщение для внешней отправки (Telegram/email/Slack)

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 0,
    "on_failure_callback": notify_failure,
}
@dag(
    dag_id="shop_product_turnover_pipeline",
    schedule="0 6 * * 1",       # каждый понедельник в 06:00
    start_date=datetime(2024, 1, 1),    # условие старта с 01.01.2024, т.к. последние записи были 31.12.2023
    catchup=False,
    default_args=default_args,
    tags=["retail", "revenue"],
)
def call_steps_airflow():
    @task
    # функция для загрузки новых строк в БД
    def load_csv_to_product():
        # читаем CSV из папки dags и вставляем новые строки в bd_shops.product.
        df = pd.read_csv("/opt/airflow/dags/product_new_data.csv")
        hook = PostgresHook(postgres_conn_id="shops_db")    # открываем наше соединение shops_db в airflow
        # описываем шаблон-правила для дальнейшего заполнения данными таблицы product
        insert_query = """
            INSERT INTO bd_shops.product
                (id, product_name, shop_id, revizion_date, count, price_sale_out, base_size)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING     
        """

        dates_set = set()
        # заполняем построчно таблицу product новыми данными из product_new_data.csv
        for row in df.iloc:
            print(row.revizion_date)
            # сохраняем set с добавленными датами в уже существующую таблицу product для создания  SQL-витрины
            dates_set.add(str(row.revizion_date))
            hook.run(insert_query,
                     parameters=(
                         int(row.id),
                         str(row.product_name),
                         int(row.shop_id),
                         str(row.revizion_date),
                         int(row["count"]),
                         float(row.price_sale_out),
                         float(row.base_size)
                        )
                     )
        print(dates_set)
        return list(dates_set)

    @task
    # Запускаем SQL-функцию с проверкой критического значения
    def update_datamart (dates_list):
        hook = PostgresHook(postgres_conn_id="shops_db")
        query = """
            INSERT INTO bd_shops.dm_daily_sales (revizion_date, sum_sales)
            SELECT p.revizion_date, SUM(p.count * p.price_sale_out) AS sales_revenue
            FROM bd_shops.product p
            GROUP BY p.revizion_date
            HAVING p.revizion_date = ANY(%s::date[])
            ORDER BY p.revizion_date DESC
        """
        hook.run(query, parameters=(dates_list,))

    @task
    # Запускаем проверку критического значения
    def check_datamart(dates_list):
        hook = PostgresHook(postgres_conn_id="shops_db")
        query = """
                SELECT count(revizion_date)  
                FROM dm_daily_sales
                WHERE revizion_date = ANY(%s::date[])
                AND sum_sales <= 5000
            """
        result = hook.get_first(query, parameters=(dates_list,))
        bad_days_count = result[0]

        if bad_days_count > 0:
            raise ValueError(
                f"Обнаружено {bad_days_count} дн. с выручкой <= 5000 среди загруженных дат"
            )

    # Шаг срабатывает, если возникает ошибка в check_datamart
    send_error_notification = EmptyOperator(
        task_id="send_error_notification",
        trigger_rule="one_failed",
    )

    # Шаг срабатывает, если ошибки в check_datamart не было, индикатор успешного завершение DAGa
    end_step = EmptyOperator(
        task_id="end_step",
        trigger_rule="all_success",
    )

    dates = load_csv_to_product()
    mart_step = update_datamart(dates)
    check_step = check_datamart(dates)

    mart_step >> check_step
    check_step >> send_error_notification
    check_step >> end_step

call_steps_airflow()