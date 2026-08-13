import pandas as pd
import os
import sqlite3
from datetime import datetime

# Генерируется один раз за запуск скрипта — это и есть "дата рана DAG"
report_period = datetime.now().strftime('%Y-%m-%d')

#Пути к файлам
input_file = 'YM_demo_attendance_for_six_months.csv'       #загруженный файл с Яндекс Метрики
output_file = 'clean_demo_data.csv'                        #файл с очищенными данными
output_file2 = 'data_indicators.csv'
db_path = 'visits.db'                                      #файл с таблицей в БД SQL
datalens_export_path = '/opt/airflow/dags/datalens_export.xlsx'  #Файл сохраняем в таблицу Excel для Datalens

def check_file_existence(file_path):
    """
    Проверяет наличие файла.

    Функция принимает путь к файлу и проверяет, существует ли файл по указанному пути.
    Если файл не найден, выбрасывается исключение FileNotFoundError.

    Аргументы:
        file_path (str): Путь к проверяемому файлу.

    Исключения:
        FileNotFoundError: Выбрасывается, если файл отсутствует по указанному пути.
    """

    if not os.path.exists(file_path):
        #Если файл не найден, выбрасывается исключение с указанием пути
        raise FileNotFoundError(f"Файл {file_path} не найден!")
    print("Файл присутствует.")

check_file_existence(input_file)

def validate_columns(file_path):
    """
        Проверяет наличие обязательных столбцов в файле.

        Функция загружает CSV-файл, проверяет наличие необходимых столбцов
        и выбрасывает исключение, если каких-либо столбцов не хватает.

        Аргументы:
            file_path (str): Путь к файлу, который необходимо проверить.

        Исключения:
            ValueError: Выбрасывается, если отсутствуют обязательные столбцы.

        Логика работы:
        1. Читаем файл с помощью pandas.
        2. Определяем список обязательных столбцов.
        3. Сравниваем обязательные столбцы с реальными столбцами из файла.
        4. Если каких-то столбцов не хватает, выбрасываем исключение с их перечнем.
        """

    #Чтение CSV-файла
    df = pd.read_csv(file_path)

    #Список обязательных столбцов
    required_column = [
        'Час визита', 'Визиты', 'Посетители', 'Просмотры',
        'Отказы', 'Глубина просмотра', 'Время на сайте', 'Визитов в день',
        'Достижения избранных целей', 'Доход по избранным целям, RUB',
        'Конверсия посетителей по избранным целям'
    ]

   #Поиск отсутствующих столбцов
    missing_column = [col for col in required_column if col not in df.columns]

    #Если отсутствуют обязательные столбцы, выбрасываем исключение
    if missing_column:
        raise ValueError(f"Отсутствуют следующие сталбцы: {missing_column}")

validate_columns(input_file)

def validate_data_quality(file_path):
    """
        Проверка данных на пустоту и корректность.

        Функция выполняет несколько проверок для оценки качества данных:
        1. Проверяет, что файл не пустой.
        2. Проверяет отсутствие пропусков в ключевых столбцах.
        3. Проверяет, что в столбце с количеством визитов нет отрицательных значений.

        Аргументы:
            file_path (str): Путь к файлу, который необходимо проверить.

        Исключения:
            ValueError: Выбрасывается при обнаружении проблем с данными.

        Логика работы:
        1. Загружаем CSV-файл в DataFrame.
        2. Удаляем первую строку, которая содержит мета-данные "Итого и среднее".
        3. Выполняем последовательные проверки на пустоту, пропуски.
        """
    #Чтение данных из файла
    df = pd.read_csv(file_path)

    # Убираем лишнюю строку "Итого и средние" из загруженного файла и выдаем сообщение
    df = df[df['Час визита'] != 'Итого и средние']

    # Выводим ошибку исключения, в случае несоответсвия кол-ву строк
    if len(df) != 24:
        raise ValueError(f"Ожидалось 24 строки, получено {len(df)}")

    #Проверка, что файл не пустой
    if df.empty:
        raise ValueError("Файл пустой.")

    #Проверка на наличие пропусков в ключевых столбцах
    if df['Час визита'].isnull().any() or df['Визиты'].isnull().any():
        raise ValueError("В данных есть пропуски в столбцах 'Час визита' или 'Визиты'.")

    #Проверка на отрицательные значения в столбце 'Визиты'
    if (df['Визиты'] < 0).any():
        raise ValueError("Столбец 'Визиты' содержит отрицательные значения.")

validate_data_quality(input_file)

def preprocess_data(input_file, output_file, report_period):
    """
        Обработка данных.

        Функция выполняет очистку и преобразование данных:
        1. Удаляет мета-данные "Итого и средние".
        2. Добавляет новые метрики:
            - долю вовлеченности.
            - конверсию посетителей по избранным целям в процентах.
            - время на сайте переводим в секунды на сайте.
        3. Сохраняет очищенные и преобразованные данные в новый файл.

        Аргументы:
            input_file (str): Путь к входному CSV-файлу с необработанными данными.
            output_file (str): Путь к выходному CSV-файлу для сохранения обработанных данных.

        Логика работы:
        1. Чтение данных из файла.
        2. Очистка и преобразование данных.
        3. Добавление новых метрик для дальнейшего анализа.
        4. Сохранение данных в новый файл.
        """
    #Чтение данных из входного файла
    df = pd.read_csv(input_file)

    #Убираем лишнюю строку "Итого и средние" из загруженного файла и выдаем сообщение
    df = df[df['Час визита'] != 'Итого и средние']

    #Выводим ошибку исключения, в случае несоответсвия кол-ву строк
    if len(df) != 24:
        raise ValueError(f"Ожидалось 24 строки, получено {len(df)}")

    #Преобразуем время на сайте в кол-во секунд на сайте
    df['second_on_site'] = pd.to_timedelta(df['Время на сайте']).dt.total_seconds()

    #Доля вовлеченной аудитории
    df['engaged_share_pcnt'] = round((1 - df['Отказы']) * 100, 2)

    #Преобразуем поле "Конверсия посетителей по избр. целям" в проценты
    df['conversion_pcnt'] = round(df['Конверсия посетителей по избранным целям'] * 100, 2)

    final_df = df[['Час визита', 'Визиты', 'Достижения избранных целей', 'Глубина просмотра',
            'second_on_site', 'engaged_share_pcnt', 'conversion_pcnt']]

    #Словарь с соответствием старых и новых названий столбцов
    column_mapping = {
        'Час визита': 'visit_hour',
        'Визиты': 'visits',
        'Достижения избранных целей': 'goal_completions',
        'Глубина просмотра': 'page_depth',
        'second_on_site': 'second_on_site',
        'engaged_share_pcnt': 'engaged_share_pcnt',
        'conversion_pcnt': 'conversion_pcnt'
    }

    #Переименование столбцов
    final_df = final_df.rename(columns=column_mapping)

    #report_period добавляем первой колонкой — так удобнее читать таблицу глазами
    final_df.insert(0, 'report_period', report_period)

    #Сохранение обработанных данных в выходной файл
    final_df.to_csv(output_file, index=False)

preprocess_data(input_file, output_file, report_period)

def check_processed_file(output_file):
    """
        Проверка преобразованного файла.

        Функция выполняет несколько проверок преобразованного файла:
        1. Проверяет, существует ли файл по указанному пути.
        2. Проверяет, что файл не пустой.
        3. Проверяет наличие обязательных столбцов, которые должны быть добавлены в ходе обработки данных.

        Аргументы:
            output_file (str): Путь к преобразованному CSV-файлу.

        Исключения:
            - FileNotFoundError, если файл не найден.
            - ValueError, если файл пуст или не содержит обязательных столбцов.
        """
    #Проверка существования файла
    if not os.path.exists(output_file):
        raise FileNotFoundError(f"Преобразованный файл {output_file} не найден")

    #Чтение данных из преобразованного файла
    df = pd.read_csv(output_file)

    #Проверка, что файл не пустой
    if df.empty:
        raise ValueError("Преобразованный файл пустой")

    #Проверка наличия обязательных столбцов
    if ('second_on_site' not in df.columns or 'engaged_share_pcnt' not in df.columns or 'conversion_pcnt' not in df.columns):
        raise ValueError("В преобразованном файле не хватате обязательных столбцов: 'second_on_site', 'engaged_share_pcnt', 'conversion_pcnt'.")

check_processed_file(output_file)

def added_metrics(output_file, output_file2, report_period):
    """
        Создание дополнительных метрик на одну строку на основе таблицы clean_demo_data.csv

        Функция выполняет создание нового файла с метриками-индикаторами для еще одной таблицы в SQL:
        1. Сумма всех визитов
        2. Средняя конверсия (средневзвешенная конверсия по визитам за сутки, а не по часам)
        3. Простое среднее по часам — для референсной линии на графике
        4. Выявляем порог "достаточного" трафика, чтобы данные с низким порогом не искажали реальные данные
        5. Считаем конверсию лучших часов

        Аргументы:
            output_file (str): Путь к входному CSV-файлу с обработанными данными.
            output2_file (str): Путь к выходному CSV-файлу для сохранения новой таблицы с даныыми.

    """
    # Чтение данных из преобразованного файла
    df = pd.read_csv(output_file)

    #Считаем сумму всех визитов в сутки
    total_visits = int(df['visits'].sum())

    #Средневзвешенная конверсия за сутки
    weighted_conversion = round((df['goal_completions'].sum() / df['visits'].sum()) * 100, 2)

    #Простое среднее по часам для референсной линии на графике
    simple_avg_conversion = round(df['conversion_pcnt'].mean(), 2)

    #Порог "достаточного" трафика — отсекаем шумные часы (медиана визитов за сутки)
    min_visits_threshold = df['visits'].median()

    #Час пиковой посещаемости
    peak_traffic_hour = df.loc[df['visits'].idxmax(), 'visit_hour']

    #Отсеиваем визиты, которые ниже порогового значения
    qualified = df[df['visits'] >= min_visits_threshold]

    #Час лучшей конверсии (среди часов с достаточным трафиком)
    best_conversion_hour = qualified.loc[qualified['conversion_pcnt'].idxmax(), 'visit_hour']

    #Составляем таблицу с одной строкой
    result_df = pd.DataFrame([{
        'report_period': report_period,
        'total_visits': total_visits,
        'weighted_conversion_pcnt': weighted_conversion,
        'simple_avg_conversion_pcnt': simple_avg_conversion,
        'min_visits_threshold': min_visits_threshold,
        'peak_traffic_hour': peak_traffic_hour,
        'best_conversion_hour': best_conversion_hour,
    }])

    #Сохранение обработанных данных в выходной файл
    result_df.to_csv(output_file2, index=False)

added_metrics(output_file, output_file2, report_period)

def init_db(db_path):
    """
        Инициализация базы данных SQLite.

        Функция выполняет следующие действия:
        1. Создает соединение с базой данных по указанному пути.
        2. Создает таблицу в базе данных, если она не существует.
        3. Выполняет команду для создания таблицы с определенной схемой.
        4. Закрывает соединение с базой данных после выполнения операции.

        Аргументы:
            db_path (str): Путь к базе данных SQLite, куда будет создана таблица.
        """
    # Устанавливаем соединение с базой данных SQLite по указанному пути
    conn = sqlite3.connect(db_path)

    # Создаем курсор для выполнения SQL-запросов
    cur = conn.cursor()

    #SQL-запрос для создания таблицы visits_data, если она не существует
    cur.execute('''
        CREATE TABLE IF NOT EXISTS visits_data (
            report_period       TEXT NOT NULL, -- Отчетный период для накопления истории, но без дублирования данных
            visit_hour          TEXT NOT NULL,    -- Час визита
            visits              INTEGER NOT NULL CHECK (visits >= 0),    -- Кол-во визитов с защитой на уровне БД от отрицательных значений 
            goal_completions    INTEGER NOT NULL CHECK (goal_completions >= 0),    -- Кол-во достижений цели с защитой на уровне БД
            page_depth          REAL,    -- Глубина просмотра
            second_on_site      REAL,  -- Время на сайте в секундах
            engaged_share_pcnt   REAL, -- Вовлеченность посетителей в процентах
            conversion_pcnt      REAL,    -- Конверсия посетителей по избранным целям в процентах
            PRIMARY KEY (report_period, visit_hour)   -- Первичные ключи для защиты от дублирования данных
        );
    ''')

    #SQL-запрос для создания таблицы attend_summary, если она не существует
    cur.execute('''
            CREATE TABLE IF NOT EXISTS attend_summary (
                report_period               TEXT PRIMARY KEY,   -- Отчетный период для накопления истории, но без дублирования данных
                total_visits                INTEGER NOT NULL,   -- Сумма визитов за сутки
                weighted_conversion_pcnt     REAL,   -- Средневзвешенная конверсия визитов за сутки
                simple_avg_conversion_pcnt   REAL,   -- Простое среднее по часам для референсной линии на графике
                peak_traffic_hour           TEXT,   -- Час пиковой посещаемости
                min_visits_threshold        REAL,   -- Пороговое значение по минимальному кол-ву визитов
                best_conversion_hour        TEXT    -- Час лучшей конверсии (среди часов с достаточным трафиком)
            );
        ''')

    #Подтверждаем изменения и записываем их в базу данных
    conn.commit()

    #Закрываем соединение с базой данных
    conn.close()

init_db(db_path)

def load_data_to_db(db_path, processed_file, metrics_file, report_period):
    """
        Загрузка обработанных данных в таблицы базы данных SQLite.

        Функция выполняет следующие действия:
        1. Открывает соединение с базой данных и созданной еще таблицей с матриками.
        2. Загружает данные из обработанных файлоф (CSV) в подготовленные таблицы.
        3. Закрывает соединение с базой данных.

        Аргументы:
            db_path (str): Путь к базе данных SQLite.
            processed_file (str): Путь к файлу с обработанными данными (CSV).
            metrics_file (str): Путь к файлу с рассчитанными метриками (CSV).
        """

    #Открываем соединение с базой данных
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    #Идемпотентность: если этот report_period (в случае ручного повторного запуска в ту же дату)
    #уже загружался — сначала стираем старую версию
    cur.execute('DELETE FROM visits_data WHERE report_period = ?', (report_period,))
    cur.execute('DELETE FROM attend_summary WHERE report_period = ?', (report_period,))
    conn.commit()

    #Читаем данные из обработанного CSV файла в DataFrame
    df = pd.read_csv(processed_file)

    #Загружаем данные в таблицу 'visits_data' в базе данных
    df.to_sql('visits_data', conn, if_exists='append', index=False)

    #Читаем данные с рассчитанными метриками из CSV файла в DataFrame
    df_metrics = pd.read_csv(metrics_file)

    #Загружаем данные в таблицу 'attend_summary' в базе данных
    df_metrics.to_sql('attend_summary', conn, if_exists='append', index=False)

    #Подтверждаем изменения и записываем их в базу данных
    conn.commit()

    #Закрываем соединение с базой данных
    conn.close()

load_data_to_db(db_path, output_file, output_file2, report_period)

def check_table_data(db_path):
    """Функция для выполнения SELECT запроса и проверки таблицы."""

    #Подключаемся к базе данных SQLite по указанному пути
    conn = sqlite3.connect(db_path)

    #Создаем курсор для выполнения SQL-запросов
    cursor = conn.cursor()

    #Выполнение SELECT запроса, чтобы получить количество строк в таблице 'visits_data'
    cursor.execute("SELECT COUNT(*) FROM visits_data;")

    #Получаем результат запроса, который возвращает кортеж с числом строк в таблице
    row_count = cursor.fetchone()[0]  #Получаем количество строк в таблице

    #Проверка, если таблица пуста (нет данных)
    if row_count == 0:
        #Если таблица пуста, выбрасываем исключение с соответствующим сообщением
        raise ValueError("Таблица 'visits_data' пуста.")

    #-------------------------------------------------------------------------------------

    #Выполнение SELECT запроса, чтобы получить количество строк в таблице 'attend_summary'
    cursor.execute("SELECT COUNT(*) FROM attend_summary;")

    #Получаем результат запроса, который возвращает кортеж с числом строк в таблице
    row_count2 = cursor.fetchone()[0]  #Получаем количество строк в таблице

    #Проверка, если таблица пуста (нет данных)
    if row_count2 == 0:
        #Если таблица пуста, выбрасываем исключение с соответствующим сообщением
        raise ValueError("Таблица 'attend_summary' пуста.")

    #-------------------------------------------------------------------------------------

    #Выполняем дополнительный запрос для получения информации о столбцах таблицы 'visits_data'
    cursor.execute("PRAGMA table_info(visits_data);")

    #Извлекаем имена всех столбцов в таблице 'visits_data' из результатов запроса
    columns = [column[1] for column in cursor.fetchall()]  #Получаем имена столбцов

    #Список обязательных столбцов, которые должны присутствовать в таблице 'visits_data'
    required_columns = ['report_period', 'visit_hour', 'visits', 'goal_completions', 'page_depth',
                        'second_on_site', 'engaged_share_pcnt', 'conversion_pcnt']

    #Проверка на отсутствие обязательных столбцов в таблице 'visits_data'
    missing_columns = [col for col in required_columns if col not in columns]

    #Если какие-либо обязательные столбцы в таблице 'visits_data' отсутствуют, выбрасываем исключение с их списком
    if missing_columns:
        raise ValueError(f"Отсутствуют обязательные столбцы в таблице 'visits_data': {', '.join(missing_columns)}")

    #-------------------------------------------------------------------------------------

    #Выполняем дополнительный запрос для получения информации о столбцах таблицы 'attend_summary'
    cursor.execute("PRAGMA table_info(attend_summary);")

    #Извлекаем имена всех столбцов в таблице 'attend_summary' из результатов запроса
    columns2 = [column[1] for column in cursor.fetchall()]  #Получаем имена столбцов

    #Список обязательных столбцов, которые должны присутствовать в таблице 'attend_summary'
    required_columns2 = ['report_period', 'total_visits', 'weighted_conversion_pcnt',
                         'simple_avg_conversion_pcnt', 'peak_traffic_hour', 'min_visits_threshold',
                         'best_conversion_hour']

    #Проверка на отсутствие обязательных столбцов в таблице 'attend_summary'
    missing_columns2 = [col for col in required_columns2 if col not in columns2]

    #Если какие-либо обязательные столбцы в таблице 'attend_summary' отсутствуют, выбрасываем исключение с их списком
    if missing_columns2:
        raise ValueError(f"Отсутствуют обязательные столбцы в таблице 'attend_summary': {', '.join(missing_columns2)}")

    #-------------------------------------------------------------------------------------

    # Закрываем соединение с базой данных
    conn.close()

check_table_data(db_path)

def export_for_datalens(db_path, output_xlsx):
    """
    Выгружает обе таблицы из SQLite в ОДИН Excel-файл, разными листами —
    для загрузки в DataLens одним подключением.
    """
    conn = sqlite3.connect(db_path)
    visits_df = pd.read_sql('SELECT * FROM visits_data', conn)
    summary_df = pd.read_sql('SELECT * FROM attend_summary', conn)
    conn.close()

    with pd.ExcelWriter(output_xlsx, engine='openpyxl') as writer:
        visits_df.to_excel(writer, sheet_name='visits_data', index=False)
        summary_df.to_excel(writer, sheet_name='attend_summary', index=False)

export_for_datalens()

def check_datalens_export(output_xlsx):
    """Проверяет, что файл существует и содержит оба непустых листа."""
    if not os.path.exists(output_xlsx):
        raise FileNotFoundError(f"Файл выгрузки {output_xlsx} не найден")

    sheets = pd.read_excel(output_xlsx, sheet_name=None)  # словарь {имя_листа: df}
    required_sheets = ['visits_data', 'attend_summary']
    missing = [s for s in required_sheets if s not in sheets]
    if missing:
        raise ValueError(f"В файле {output_xlsx} отсутствуют листы: {missing}")

    for name, df in sheets.items():
        if df.empty:
            raise ValueError(f"Лист {name} в {output_xlsx} пустой")

    print("Excel-файл для DataLens готов, оба листа на месте.")

check_datalens_export()