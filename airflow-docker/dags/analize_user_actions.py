from airflow.operators.python import PythonOperator
from airflow import DAG
import os
import sqlite3
from datetime import datetime
import pandas as pd
import plotly.express as px

#Задаем Default arguments for the DAG
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 1,
}

#ЭТАП 1
#Проверка наличия файла БД
def check_file_excistence():
    """
    Проверяет наличие файла DZ_user_actions.csv.
    :return: Ошибка, если отсутствует указанный файл
    """
    file = '/opt/airflow/dags/DZ_user_actions.csv'
    if not os.path.exists(file):
        raise FileNotFoundError(f"Файл {file} не найден!")
    print("Файл присутствует.")

#Проверяем структуру csv-файла
def validate_db_file():
    """
    Проверяет наличие всех обязательных столбцов и корректные типы данных
    :return: Сообщение о каждой ошибке или успешном прохождении проверки
    """
    required_columns = ['user_id', 'product_id', 'action', 'category', 'price', 'timestamp']

    try:
        #Чтение файла
        df = pd.read_csv('/opt/airflow/dags/DZ_user_actions.csv')
        #Приведем сразу поле timestamp к нужному типа для дальнейшей корректной агрегации
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        #Проверка наличия обязательных столбцов
        missing_column = [col for col in required_columns if col not in df.columns]
        if missing_column:
            raise ValueError(f"Отсутствуют следующие сталбцы в DZ_user_actions.csv: {missing_column}")

        #Проверка типов данных
        type_check = {
            'user_id': 'int64',
            'product_id': 'int64',
            'action': 'object',
            'category': 'object',
            'price': 'float64',
            'timestamp': 'datetime64[ns]'
        }
        for col, dtype in type_check.items():
            if df[col].dtype != dtype:
                raise TypeError(f"Некорректный тип данных для столбца {col}. Ожидается {dtype}, но получено {df[col].dtype}")

        print("Файл DZ_user_actions.csv успешно прошел проверку.")
    except Exception as exp:
        raise ValueError(f"Ошибка при проверке файла DZ_user_actions.csv: {exp}")

#Загрузка csv файла в SQLite3
def load_data_to_sql():
    """
    Загрузка файла DZ_user_actions.csv в базу данных SQLite
    :return: Сообщение об успешной загрузке данных в БД или об ошибке загрузки
    """
    try:
        #Подключение к базе данных из python. Если подключения нет, то SQLite создаст БД
        conn = sqlite3.connect('/opt/airflow/dags/user_actions_db')
        cursor = conn.cursor()

        #Создание таблицы, если она не существует
        # id — суррогатный автоинкрементный ключ, присваивается каждой новой строке
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_product (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            action TEXT,
            category TEXT,
            price REAL,
            timestamp TEXT,
            UNIQUE(user_id, product_id, action, timestamp)
        )
        ''')

        #Чтение и загрузка данных из DZ_user_actions.csv
        df_user_product = pd.read_csv('/opt/airflow/dags/DZ_user_actions.csv')
        data_to_insert = df_user_product[['user_id', 'product_id', 'action', 'category', 'price', 'timestamp']].values.tolist()

        #Проверка на Unique значения, чтобы не клонировать данные в БД
        cursor.executemany('''
                   INSERT OR IGNORE INTO user_product (user_id, product_id, action, category, price, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)
               ''', data_to_insert)

        # Сохранение изменений и закрытие соединения
        conn.commit()
        print(f"Обработано {len(data_to_insert)} строк из CSV.")
        conn.close()
    except Exception as exp:
        raise ValueError(f"Ошибка при загрузке данных в SQLite: {exp}")

#Проверка качества данных после загрузки в SQLite
def validate_loaded_data():
    """
    Проверяет качество загрузки данных в SQL: кол-во строк, дубликаты, пропущенные значения.
    :return: Сообщение об успешной загрузке или ошибка этапа загрузки.
    """
    try:
        #Подключение к БД, в которой проверяем данные в таблице user_product
        conn = sqlite3.connect('/opt/airflow/dags/user_actions_db')
        cursor = conn.cursor()

        #1. Проверка кол-ва строк
        def check_row_count(table_name, csv_file):
            #Число строк в таблице SQLite user_product
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            db_row_count = cursor.fetchone()[0]   #Получаем первую (единственную) строку в результате selectа

            #Число строк в файле DZ_user_actions.csv
            df_csv = pd.read_csv(csv_file)
            csv_row_count = len(df_csv)   #Забираем кол-во строк и DZ_user_actions.csv

            #Проверка на несоответствие строк csv и БД
            if db_row_count != csv_row_count:
                raise ValueError(f"Несоответствие количества строк в {table_name} и {csv_file}. В CSV: {csv_row_count}, в БД: {db_row_count}")

        check_row_count('user_product', '/opt/airflow/dags/DZ_user_actions.csv')

        #2. Проверка наличия дубликатов
        def check_dublicates(table_name, columns):
            columns_str = ', '.join(columns)
            cursor.execute(f"SELECT {columns_str}, count(*) FROM {table_name} GROUP BY {columns_str} HAVING count(*) > 1")
            dublicates = cursor.fetchall()  #Собираем по всем данным поля
            if dublicates:
                raise ValueError(f"Обнаружены дубликаты в {table_name}: {dublicates}")

        check_dublicates('user_product', ['user_id', 'product_id', 'action', 'category', 'price', 'timestamp'])

        print("Проверка на дубликаты успешно пройдена")

        #3. Проверка на пропущенные значения
        def check_missing_values(table_name, columns):
            for col in columns:
                #Проходимся по столбцам таблицы user_product и проверяем на значения пустые ячейки
                cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {col} IS NULL")
                missing_count = cursor.fetchone()[0]
                if missing_count > 0:
                    raise ValueError(f"Обнаружены пропущенные значения в столбце {col} таблицы {table_name}")

        check_missing_values('user_product', ['user_id', 'product_id', 'action', 'category', 'price', 'timestamp'])

        print("Проверка на пропущенные значения успешно пройдена")

    except Exception as exp:
        raise ValueError(f"Ошибка при проверке качества данных: {exp}")
    finally:
        conn.close()

#ЭТАП 2
#Используем SQL-запросы для извлечение показателей
def calc_top_product_from_action():
    """
    Рассчитываем топ товаров для каждого действия: кол-во просмотров, добавления в корзину, покупки
    :return: DataFrame результатом списка по 3м действиям
    """
    #Подключение к базе данных SQLite
    conn = sqlite3.connect('/opt/airflow/dags/user_actions_db')

    try:
        #SQL-запрос для расчета топ товаров по действию
        query = '''
            SELECT action, product_id, cnt
            FROM(
                SELECT
                    action,
                    product_id,
                    COUNT(*) as cnt,
                    ROW_NUMBER() OVER(PARTITION BY action ORDER BY COUNT(*) DESC) as row_num
                FROM user_product
                GROUP BY action, product_id
                )
            WHERE row_num = 1
        '''

        #Выполнение запроса и получение результата в DataFrame
        top_prod_actn = pd.read_sql(query, conn)

        #Возвращаем результаты в виде DataFrame
        return top_prod_actn

    finally:
        #Закрытие соединения с базой данных независимо от того, были ли ошибки
        conn.close()

#Сохранение результатов запроса в файл Excel
def save_result_to_excel():

    #Подключение к БД SQLite
    conn = sqlite3.connect('/opt/airflow/dags/user_actions_db')

    try:
        #Выполняем SQL-запрос
        top_product_from_action = calc_top_product_from_action()

        #Создаем Excel-файл с помощью pandas
        with pd.ExcelWriter('/opt/airflow/dags/analytics_result.xlsx', engine='openpyxl') as writer:
            top_product_from_action.to_excel(writer, sheet_name='Top_product', index=False)     #Лист 'Top_product'

        print("Результаты успешно сохранены в analytics_result.xlsx")

    except Exception as exp:
        print(f"Ошибка при сохранении результов в Excel: {exp}")

    finally:
        #Закрываем соединение с БД
        conn.close()

#ЭТАП 3
#Извлекаем показатели с помощью Python

#Рассчитываем общую выручку по категориям
def calculate_revenue():
    """
    Рассчитываем общую выручку товаров по категориям, а также долю выручки для каждой категории
    :return: Таблицу с данными
    """

    #Подключение к БД SQLite
    conn = sqlite3.connect('/opt/airflow/dags/user_actions_db')

    #Извлечение данных об общей выручке по категориям
    query = '''
        SELECT category, SUM(price) as sum_revenue
        FROM user_product
        WHERE action = 'purchase'
        GROUP BY category
        HAVING sum(price)
        ORDER BY sum(price) DESC
    '''

    #Выполнение запроса и сохранение результатов в DataFrame
    df = pd.read_sql(query, conn)

    #Закрытие соединения с БД
    conn.close()

    #Расчет доли выручки по категориям от общей выручки в процентах
    df['revenue_share'] = df['sum_revenue'] / df['sum_revenue'].sum() * 100

    #Возвращаем DataFrame с тремя столбцами: category, sum_revenue, revenue_share
    return df[['category', 'sum_revenue', 'revenue_share']]

#Анализ конверсии между действиями
def analyze_covert():
    """
    Рассчитываем конверсию между действиями (общая картина без разбивки по пользователям и timestamp)
    :return: DataFrame с долей каждого действия в процентах
    """

    #Подключение к БД SQLite
    conn = sqlite3.connect('/opt/airflow/dags/user_actions_db')

    #Извлечение данных по действиям и расчет конверсии
    query = '''
        SELECT
            COUNT(CASE WHEN action = 'view' THEN 1 END) as count_views,
            COUNT(CASE WHEN action = 'add_to_cart' THEN 1 END) as count_add_to_cart,
            COUNT(CASE WHEN action = 'purchase' THEN 1 END) as count_purchases
        FROM user_product
    '''

    #Выполнение SQL-запроса и сохранение результатов в DataFrame
    df = pd.read_sql(query, conn)

    # Закрытие соединения с БД
    conn.close()

    #Считаем конверсию в процентах
    df['conv_view_to_cart'] = df['count_add_to_cart'] / df['count_views'] * 100
    df['conv_cart_to_purchase'] = df['count_purchases'] / df['count_add_to_cart'] * 100

    #Возвращаем DataFrame с 5ю столбцами
    return df[['count_views', 'count_add_to_cart', 'count_purchases', 'conv_view_to_cart', 'conv_cart_to_purchase']]

#Построение интерактивного графика и сохранение его в HTML-файл
def create_trend_chart_by_category():
    """
    Строим график распределения популярности товаров по категориям и месяцам
    :return: HTML-файл
    """
    # Подключение к БД SQLite
    conn = sqlite3.connect('/opt/airflow/dags/user_actions_db')

    # Извлечение данных о популярности товаров на каждом этапе действия по категориям и месяцам
    query = '''
            SELECT 
                strftime('%Y-%m', timestamp) as month,
                category,
                action, 
                COUNT(*) as count_prod
            FROM user_product
            GROUP BY category, action, month
            ORDER BY category, month ASC
        '''

    # Выполнение запроса и сохранение результатов в DataFrame
    df = pd.read_sql(query, conn)

    # Закрытие соединения с БД
    conn.close()

    #Создание интерактивного графика с разбивкой по категориям
    fig = px.line(
        df,                 #данные для графика
        x='month',
        y='count_prod',
        color='category',
        facet_col='action',
        title='Распределение популярности товаров по категориям',
        labels={'month': 'Месяц',
                'count_prod': 'Кол-во товаров',
                'category': 'Категория'},
        template='plotly_dark'
    )

    #Убираем префикс "action=" из заголовков подграфиков
    fig.for_each_annotation(lambda a: a.update(text=a.text.replace("action=", "")))

    #Добавление дополнительных элементов на графике
    fig.update_layout(
        xaxis_title="Месяц",
        yaxis_title="Кол-во товаров",
        font=dict(size=14),
        hovermode='x unified',
        legend_title="Категории"
    )

    #Сохранение графика в HTML-файл
    output_file = '/opt/airflow/dags/trend_chart_by_category.html'    #имя выходного файла
    fig.write_html(output_file)                     #сохранение графика в HTML-файл

    print(f"График успешно сохранен в {output_file}")

#Сохранение результатов функций в один файл Excel
def save_all_analysis_to_excel():
    """
    Сохраняем все результаты аналитических функций в один файл Excelна разные листы
    :return: файл Excel
    """
    #Шаг 1: Выполнение всех аналитических функций
    revenue_cat = calculate_revenue()   #общая выручка товаров по категориям и доля в процентах
    convertion = analyze_covert ()      #анализ конверсии между действиями

    #Шаг 2: Создание файла Excel
    with pd.ExcelWriter('/opt/airflow/dags/analytics_results.xlsx', engine='openpyxl') as writer:
        #Запись каждого DataFrame на отдельный лист
        revenue_cat.to_excel(writer, sheet_name='Revenue_category', index=False),
        convertion.to_excel(writer, sheet_name='Convertion', index=False)

    print("Все аналитические данные успешно сохранены в analytics_results.xlsx")

#Создаем DAG
dag_create = DAG(
    'data_validation_and_loading_dag',
    default_args=default_args,
    description='DAG для проверки и загрузки данных в SQLite',
    schedule=None,      #Пайплан не будет запускаться по расписанию
    start_date=datetime(2025, 1, 1),     #Начальная дата запуска
    catchup=False,              #Не выполнять пропущенные запуски
)

#Task 1: Проверка наличия файла БД
check_files_task = PythonOperator(
    task_id='check_file_excistence',
    python_callable=check_file_excistence,
    dag=dag_create,
)

#Task 2: Проверка структуры csv-файла
validate_db_file_task = PythonOperator(
    task_id='validate_db_file',
    python_callable=validate_db_file,
    dag=dag_create,
)

#Task 3: Загрузка csv файла в SQLite3
load_data_task = PythonOperator(
    task_id='load_data_to_sql',
    python_callable=load_data_to_sql,
    dag=dag_create,
)

#Task 4: Проверка качества данных после загрузки в SQLite
validate_loaded_data_task = PythonOperator(
    task_id='validate_loaded_data',
    python_callable=validate_loaded_data,
    dag=dag_create,
)

#Task 5: Расчёт топ товаров для каждого действия: кол-во просмотров, добавления в корзину, покупки
top_product_from_action_task = PythonOperator(
    task_id='calc_top_product_from_action',
    python_callable=calc_top_product_from_action,
    dag=dag_create,
)

#Task 6: Сохранение результатов запроса в файл Excel
save_result_to_excel_task = PythonOperator(
    task_id='save_result_to_excel',
    python_callable=save_result_to_excel,
    dag=dag_create,
)

#Task 7: Расчёт общей выручки по категориям
calculate_revenue_task = PythonOperator(
    task_id='calculate_revenue',
    python_callable=calculate_revenue,
    dag=dag_create,
)

#Task 8: Расчёт конверсии между действиями
analyze_covert_task = PythonOperator(
    task_id='analyze_covert',
    python_callable=analyze_covert,
    dag=dag_create,
)

#Task 9: Построение интерактивного графика
create_trend_chart_by_category_task = PythonOperator(
    task_id='create_trend_chart_by_category',
    python_callable=create_trend_chart_by_category,
    dag=dag_create,
)

#Task 10: Сохранение результатов функций в один файл Excel
save_all_analysis_to_excel_task = PythonOperator(
    task_id='save_all_analysis_to_excel',
    python_callable=save_all_analysis_to_excel,
    dag=dag_create,
)

#Определение порядка выполнения задач
check_files_task >> validate_db_file_task >> load_data_task >> validate_loaded_data_task \
>> top_product_from_action_task \
>> save_result_to_excel_task >> [
                                    calculate_revenue_task,
                                    analyze_covert_task
                                ] \
>> create_trend_chart_by_category_task >> save_all_analysis_to_excel_task