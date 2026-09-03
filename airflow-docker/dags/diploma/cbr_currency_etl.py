import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # вычисляет абсолютный путь к папке для br_currency_transform
from datetime import datetime
import pendulum
from airflow.sdk import dag, task
from airflow.providers.postgres.hooks.postgres import PostgresHook
from cbr_currency_transform import extract_cbr_rates, transform_cbr_rates  # готовые функции

#Создаем DAG
@dag(
    dag_id="cbr_exchange_rates_etl",
    schedule="30 19 * * *",       # каждый день в 19:30 МСК — зафиксировали ранее
    start_date=pendulum.datetime(2026, 7, 1, tz="Europe/Moscow"),   # библиотека для корректной обработки часовых поясов
    catchup=True,
    tags=["diploma", "cbr"],      # теги для поиска daga
)
def cbr_exchange_rates_etl():

    @task
    def get_tracked_currencies_task() -> list[str]:
        """
        Достаёт char_code валют, которые нужно отслеживать,
        из DDl (по сути справочника) dim_currency (is_tracked = true).
        """
        hook = PostgresHook(postgres_conn_id="diploma_db")
        conn = hook.get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT char_code FROM dim_currency WHERE is_tracked = true;")
            return [row[0] for row in cur.fetchall()]

    @task
    def extract_task(ds: str) -> list[dict]:
        """
        Конвертирует дату запуска Airflow (ds, формат YYYY-MM-DD) в формат,
        который ожидает параметр date_req в API ЦБ (DD/MM/YYYY),
        и вызывает extract_cbr_rates с этой датой.
        """
        date_req = datetime.strptime(ds, "%Y-%m-%d").strftime("%d/%m/%Y")
        return extract_cbr_rates(date_req)

    @task
    def transform_task(raw_rates: list[dict], tracked_codes: list[str]) -> list[dict]:
        return transform_cbr_rates(raw_rates, tracked_codes)

    @task
    def validate_and_load_task(transformed: list[dict], tracked_codes: list[str]) -> None:
        received = {r["char_code"] for r in transformed}
        missing = [c for c in tracked_codes if c not in received]
        if missing:
            raise ValueError(f"Не пришли курсы по валютам: {missing}")

        hook = PostgresHook(postgres_conn_id="diploma_db")
        conn = hook.get_conn()
        with conn.cursor() as cur:
            for rate in transformed:
                cur.execute("""
                    DELETE FROM fact_exchange_rate
                    WHERE rate_date = %(rate_date)s AND currency_id = (
                        SELECT currency_id 
                        FROM dim_currency
                        WHERE char_code = %(char_code)s)
                """, rate)
                cur.execute("""
                    INSERT INTO fact_exchange_rate
                        (currency_id, rate_date, nominal, value, rate_per_unit, loaded_at)
                    SELECT currency_id, %(rate_date)s, %(nominal)s, %(value)s, %(rate_per_unit)s, now()
                    FROM dim_currency
                    WHERE char_code = %(char_code)s
                    ON CONFLICT (currency_id, rate_date)
                    DO UPDATE SET
                        value = EXCLUDED.value,
                        rate_per_unit = EXCLUDED.rate_per_unit,
                        loaded_at = EXCLUDED.loaded_at;
                """, rate)
        conn.commit()

    # связка тасков — вот он, ответ на "откуда что берётся"
    tracked_codes = get_tracked_currencies_task()
    raw_rates = extract_task()
    transformed = transform_task(raw_rates, tracked_codes)
    validate_and_load_task(transformed, tracked_codes)


cbr_exchange_rates_etl()