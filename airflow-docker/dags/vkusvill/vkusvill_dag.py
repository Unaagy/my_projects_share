from airflow.operators.python import PythonOperator
from airflow import DAG
import os
import sqlite3
from datetime import datetime
import pandas as pd

#Задаем Default arguments for the DAG
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 1,
}
def check_file_existence(file_path):
    """
    Проверяет наличие файлов.

    Функция принимает путь к файлам и проверяет, существует ли файлы по указанному пути.
    Если файл не найден, выбрасывается исключение FileNotFoundError.
    """

    if not os.path.exists(file_path):
        # Если файл не найден, выбрасывается исключение с указанием пути
        raise FileNotFoundError(f"Файл {file_path} не найден!")
    print("Файл присутствует.")

def read_source_file(file_path):
    """
    Функция для чтения файла
    """
    check_file_existence(file_path)
    return pd.read_csv(file_path)

def validate_columns(df, columns_list):
    """
        Проверяет наличие обязательных столбцов в каждом файле.

        Функция загружает CSV-файл, проверяет наличие необходимых столбцов
        и выбрасывает исключение, если каких-либо столбцов не хватает.
    """
   # Поиск отсутствующих столбцов в файле input_file1
    missing_columns = [col for col in columns_list if col not in df.columns]

    # Если отсутствуют обязательные столбцы, выбрасываем исключение
    if missing_columns:
        raise ValueError(f"Отсутствуют следующие столбцы: {columns_list}")

def validate_datetime_column(df: pd.DataFrame, column: str = 'datetime'):
    """
        Преобразование поля datetime в обоих файлах в нужный тип данных.

        Функция выполняет несколько операций:
        1. Подсчитывает кол-во строк до корректировки типа
        2. Преобразует поле datetime в формат дат
        3. Подсчитывает кол-во строк преобразованных в нужный тип
        4. Проверяет на условие равенства кол-ва строк до и после преобразования
    """
    # Считаем кол-во строк в поле до преобразования типа
    raw_nulls = df[column].isna().sum()
    # Преобразуем тип, используем errors='coerce' - чтобы не падала функция и продолжала преобразование
    df[column] = pd.to_datetime(df[column], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    # Считаем кол-во строк в поле после преобразования типа
    new_nulls = df[column].isna().sum()

    # Условие проверки все ли строки распознались как дата, если нет, выводим ошибку
    if new_nulls > raw_nulls:
        bad_rows = df[df[column].isna()]
        print(f"Не распарсилось {new_nulls - raw_nulls} значений в '{column}', примеры:")
        print(bad_rows.head(10))    # смотрим, что там за мусор в строках
        raise ValueError(f"validate_datetime_column: {new_nulls - raw_nulls} строк с некорректным '{column}'")

def validate_data_quality(df_events, df_orders):
    """
        Проверка данных на пустоту и корректность.

        Функция выполняет несколько проверок для оценки качества данных:
        1. Проверяет, что файл не пустой.
        2. Проверяет, что в столбце revenue нет отрицательных значений.
        3. Проверяет дублирование строк с столбцах файла input_file1.
        """
    # Проверка, что файл не пустой
    if df_events.empty or df_orders.empty:
        raise ValueError(f"Файл {df_events} и/или {df_orders} пустой.")

    # Проверка на отрицательные значения в столбце 'revenue' в файле orders.csv
    if (df_orders['revenue'] < 0).any():
        raise ValueError("Столбец 'revenue' содержит отрицательные значения.")

    # Проверка на дублирование строк с столбцах файла input_file1
    dup_row = df_events.duplicated(keep=False)     # keep=False позволяет записывать не только дублирующие строки, но и их оригиналы
    n_dup = dup_row.sum()

    if n_dup > 0:
        bad_rows = df_events[dup_row].sort_values(list(df_events.columns))   # Выводим сортированный список по полям с дублирующимися строками
        print(f"Найдено {n_dup} полностью дублирующихся строк:")
        print(bad_rows.head(10))
        raise ValueError(f"validate_no_full_duplicates: {n_dup} дублирующихся строк")

def validate_null_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """
        Функция выполняет проверку на пропуски в файле events:
        1. Проверка на пропуски обязательных столбцов 'user_id', 'event_name', 'page' в файле events
        2. Специальная проверка с условием одновременного ненулевого значения.
    """
    errors = []

    # Пропуски в обязательных для всех строк колонках
    required_cols = ['user_id', 'event_name', 'page']
    null_counts = df[required_cols].isna().sum()
    cols_with_nulls = null_counts[null_counts > 0]

    if len(cols_with_nulls) > 0:
        for col, cnt in cols_with_nulls.items():
            print(f"Пропуски в обязательной колонке '{col}': {cnt} строк")
            print(df[df[col].isna()].head(5))
        errors.append(f"Пропуски в обязательных колонках: {dict(cols_with_nulls)}")

    # product_id равен null только с событием view
    bad_product = df[
        ((df['event_name'] == 'view') & df['product_id'].notna()) |
        ((df['event_name'] != 'view') & df['product_id'].isna())
    ]
    if len(bad_product) > 0:
        errors.append(f"{len(bad_product)} строк с нарушением паттерна product_id")
        print("Примеры нарушений product_id:")
        print(bad_product.head(5))

    # order_id не null только с событием purchase
    bad_order = df[
        ((df['event_name'] == 'purchase') & df['order_id'].isna()) |
        ((df['event_name'] != 'purchase') & df['order_id'].notna())
    ]
    if len(bad_order) > 0:
        errors.append(f"{len(bad_order)} строк с нарушением паттерна order_id")
        print("Примеры нарушений order_id:")
        print(bad_order.head(5))

    if errors:
        raise ValueError("validate_null_patterns: " + "; ".join(errors))

    return df

def validate_no_nulls(df: pd.DataFrame, required_cols: list) -> pd.DataFrame:
    """
        Проверяет отсутствие пропусков в перечисленных обязательных колонках.
        В отличие от validate_null_patterns, не привязана к event_name подходит для файлов без условной логики по типу события (как orders.csv).

    """
    null_counts = df[required_cols].isna().sum()
    cols_with_nulls = null_counts[null_counts > 0]

    if len(cols_with_nulls) > 0:
        for col, cnt in cols_with_nulls.items():
            print(f"Пропуски в обязательной колонке '{col}': {cnt} строк")
            print(df[df[col].isna()].head(5))
        raise ValueError(f"validate_no_nulls: пропуски в колонках {dict(cols_with_nulls)}")

    return df

def validate_no_duplicate_order_id(df: pd.DataFrame, column: str = 'order_id') -> pd.DataFrame:
    """
        Функция выполняет проверку на дублирование строк поля 'order_id' в файлах
        1. Проверяет дублирующие строки поля 'order_id' в df_events при вызове
            validate_no_duplicate_order_id(orders)
        2. Проверяет дублирующие строки поля 'order_id' в df_events при вызове
            purchase_events = events[events['event_name'] == 'purchase']
            validate_no_duplicate_order_id(purchase_events)
            Это важно, чтобы воронка/конверсия не задвоилась
    """
    dup_row = df[column].duplicated(keep=False)
    n_dup = dup_row.sum()

    if n_dup > 0:
        bad_rows = df[dup_row].sort_values(column)
        print(f"Найдено {n_dup} строк с дублирующимся '{column}':")
        print(bad_rows.head(10))
        raise ValueError(f"validate_no_duplicate_order_id: {n_dup} дублирующихся строк по '{column}'")

    return df

def validate_known_values(df: pd.DataFrame, column: str, allowed_values: set) -> pd.DataFrame:
    """
        Функция выполняет проверку наличия только допустимых событий в поле event_name:
        1. Считает кол-во событий, не вошедших в сет known_event_names.
        2. Если таких нет, выводит сообщение, что таких строк 0. В противном случае выводит сообщение об ошибке.
    """
    bad_event = ~df[column].isin(allowed_values)
    n_bad = bad_event.sum()

    if n_bad > 0:
        bad_rows = df[bad_event]
        unexpected = set(bad_rows[column].unique())
        print(f"Найдено {n_bad} строк с неизвестными значениями '{column}': {unexpected}")
        print(bad_rows.head(10))
        raise ValueError(f"validate_known_values: неизвестные значения в '{column}': {unexpected}")

    return df

def build_unified_events(events: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    """
    Функция объединяет events.csv и orders.csv в одну таблицу на уровне события:
    к каждому purchase-событию в events добавляется revenue из orders
    (по order_id). Для остальных event_name (view/click/add) revenue = NaN,
    т.к. в orders.csv их нет и не должно быть.
    Не меняет исходные events/orders — используется как подготовительный
    шаг перед расчётом всех метрик (воронка, деньги, retention).
    """
    unified = events.merge(orders[['order_id', 'revenue']], on='order_id', how='left')

    # Защитная проверка: join не должен ни дублировать, ни терять строки
    if len(unified) != len(events):
        raise ValueError(
            f"build_unified_events: после join строк стало {len(unified)}, "
            f"было {len(events)} — вероятно, дубли order_id в orders.csv"
        )

    # Защитная проверка: revenue заполнен ровно у purchase, и только у purchase
    bad_revenue = unified[
        ((unified['event_name'] == 'purchase') & unified['revenue'].isna()) |
        ((unified['event_name'] != 'purchase') & unified['revenue'].notna())
    ]
    if len(bad_revenue) > 0:
        raise ValueError(f"build_unified_events: {len(bad_revenue)} строк с неожиданным revenue")

    return unified

def calc_funnel_metrics(unified: pd.DataFrame) -> dict:
    """
    Функция считает воронку view -> add -> purchase на основе unified-таблицы
    dimension_type ('overall'/'page') различает разрез,
    dimension_value - конкретное значение ('ALL' для overall, имя страницы для page):
    - overall: воронка и конверсии в целом
    - by_page: воронка в разрезе page, конверсия своя для каждого типа страницы (см. комментарии
    внутри — разные страницы поддерживают разные шаги воронки, единая формула конверсии для всех была бы неверной)
    """

    df = unified.copy()
    def unique_users(group_cols: list) -> pd.DataFrame:
        """
        Функция считает число уникальных пользователей (user_id) по каждому event_name,
        в разрезе, заданном через group_cols, и разворачивает event_name
        из значений в отдельные колонки (view/click/add/purchase).
        """
        if group_cols:
            gr_col = df.groupby(group_cols + ['event_name'])['user_id'].nunique().unstack(fill_value=0).reset_index() # unstack для Series с двухуровневым индексом (поле + event_name)
        else:
            gr_col  = df.groupby('event_name')['user_id'].nunique().to_frame().T.reset_index(drop=True) # используем to_frame для преобразования serias в Dataframe
        # защита от отсутствующих колонок в таблице gr_col
        for col in ['view', 'click', 'add', 'purchase']:
            if col not in gr_col .columns:
                gr_col[col] = 0
        return gr_col.rename(columns={'view': 'view_count', 'click': 'click_count', 'add': 'add_count', 'purchase': 'purchase_count'})

    # воронка и конверсии в целом
    overall = unique_users([])
    overall['dimension_type'] = 'overall'
    overall['dimension_value'] = 'ALL'
    # конверсия view->add в целом по всем страницам сразу (и прямое добавление с листинга, и через pdp)
    overall['view_to_add_pct'] = (overall['add_count'] / overall['view_count'] * 100).round(1)
    # конверсия add->purchase в целом - какая доля добавивших товар в итоге доходит до оплаты
    overall['add_to_purchase_pct'] = (overall['purchase_count'] / overall['add_count'] * 100).round(1)
    # сквозная конверсия view->purchase - итоговая эффективность воронки от просмотра до покупки
    overall['view_to_purchase_pct'] = (overall['purchase_count'] / overall['view_count'] * 100).round(1)

    # воронка в разрезе page, конверсия своя для каждого типа страницы
    by_page = unique_users(['page'])
    by_page['dimension_type'] = 'page'
    by_page['dimension_value'] = by_page['page'].astype(str)
    by_page = by_page.drop(columns=['page'])    # удаляем колонку page, скопированную в 'dimension_value'
    by_page['view_to_add_pct'] = pd.NA       # колонка пустая - тип колонки становится object
    by_page['click_to_add_pct'] = pd.NA      # колонка пустая - тип колонки становится object
    by_page['view_to_purchase_pct'] = pd.NA  # колонка пустая - тип колонки становится object

    # отбираем страницы-листинги, где add происходит напрямую с той же страницы, что и view
    mask_listing = by_page['dimension_value'].isin(['catalog', 'search', 'recommendations'])
    # считаем view->add только для этих страниц; строки cart/pdp/main_page не трогаем -
    # там view_to_add_pct остаётся pd.NA, т.к. эта конверсия для них не применима
    by_page.loc[mask_listing, 'view_to_add_pct'] = (
        by_page.loc[mask_listing, 'add_count'] / by_page.loc[mask_listing, 'view_count'] * 100
    ).round(1)

    # отбираем строку pdp — там нет view, воронка начинается с click (переход в карточку товара)
    mask_pdp = by_page['dimension_value'] == 'pdp'
    # конверсия click->add только для pdp: доля кликнувших в карточку, кто добавил товар в корзину
    by_page.loc[mask_pdp, 'click_to_add_pct'] = (
        by_page.loc[mask_pdp, 'add_count'] / by_page.loc[mask_pdp, 'click_count'] * 100
    ).round(1)

    # отбираем строку cart — там нет add, только view корзины и сама покупка
    mask_cart = by_page['dimension_value'] == 'cart'
    # конверсия view->purchase только для cart: доля просмотревших корзину, кто оформил заказ
    by_page.loc[mask_cart, 'view_to_purchase_pct'] = (
        by_page.loc[mask_cart, 'purchase_count'] / by_page.loc[mask_cart, 'view_count'] * 100
    ).round(1)

    mart_funnel = pd.concat([overall, by_page], ignore_index=True, sort=False)
    cols = ['dimension_type', 'dimension_value', 'view_count', 'click_count', 'add_count', 'purchase_count',
            'view_to_add_pct', 'click_to_add_pct', 'add_to_purchase_pct', 'view_to_purchase_pct']

    return mart_funnel[cols]

def calc_retention_metrics(unified: pd.DataFrame, day_offsets: list = [1, 3, 7, 14]) -> dict:
    """
    Функция считает retention на основе purchase-событий из unified-таблицы:
    - day_n_curve: Day-N retention curve — доля пользователей, вернувшихся
      с повторным заказом в течение N дней после первого заказа (n из day_offsets)
    - monthly_repeat_rate: доля покупателей месяца с >=2 заказами за этот месяц
    - cohort_scaffold: пустая заготовка под полноценные месячные когорты
      (cohort_month x activity_month) — наполнится, когда появится 2+ месяца данных
    """
    # берём только покупки — retention считается по факту повторного заказа
    purchases = unified[unified['event_name'] == 'purchase'].copy()
    # обрезаем время, оставляем только дату — нужна для арифметики "через N дней"
    purchases['date'] = purchases['datetime'].dt.normalize()

    # дата первого заказа каждого пользователя — точка отсчёта для Day-N
    first_order = purchases.groupby('user_id')['date'].min().rename('first_order_date')
    # прикрепляем first_order_date к каждой строке покупок, чтобы сравнивать с ней
    p = purchases.merge(first_order, on='user_id')
    # последняя дата в датасете — граница, дальше которой данных для проверки возврата нет
    max_date = purchases['date'].max()

    rows = []
    for n in day_offsets:
        # в когорту берём только тех, у кого есть полные N дней "запаса" после первого
        # заказа до конца датасета — иначе недавние пользователи занизят retention
        # не по своей вине, а просто потому что для них ещё не прошло N дней
        cohort = first_order[first_order <= max_date - pd.Timedelta(days=n)]
        cohort_size = len(cohort)
        if cohort_size == 0:
            rows.append({'day_offset': n, 'cohort_size': 0, 'returned_users': 0, 'retention_pct': None})
            continue
        # среди когорты ищем тех, кто сделал повторный заказ (после первого,
        # но не позже чем через N дней от первого)
        returned = p[
            (p['user_id'].isin(cohort.index)) &
            (p['date'] > p['first_order_date']) &
            (p['date'] <= p['first_order_date'] + pd.Timedelta(days=n))
        ]
        returned_users = returned['user_id'].nunique()
        rows.append({'day_offset': n, 'cohort_size': cohort_size, 'returned_users': returned_users,
                     'retention_pct': round(returned_users / cohort_size * 100, 1)})
    day_n_curve = pd.DataFrame(rows)

    # приводим дату к первому числу месяца — группировка для помесячной метрики
    purchases['month_start'] = purchases['date'].values.astype('datetime64[M]')
    # число заказов каждого пользователя в каждом месяце
    per_user_month = purchases.groupby(['month_start', 'user_id']).size().reset_index(name='orders_in_month')
    # всего уникальных покупателей за месяц
    monthly = per_user_month.groupby('month_start').agg(total_buyers=('user_id', 'nunique')).reset_index()
    # из них — те, у кого 2+ заказа за месяц
    repeat = per_user_month[per_user_month['orders_in_month'] >= 2].groupby('month_start').agg(repeat_buyers=('user_id', 'nunique')).reset_index()
    # объединяем; месяц без повторных покупателей получит repeat_buyers=0, а не пропуск
    monthly = monthly.merge(repeat, on='month_start', how='left').fillna({'repeat_buyers': 0})
    monthly['repeat_buyers'] = monthly['repeat_buyers'].astype(int)
    monthly['repeat_rate_pct'] = (monthly['repeat_buyers'] / monthly['total_buyers'] * 100).round(1)

    # заготовка под полноценные месячные когорты (когорта первой покупки x месяц активности) —
    # сейчас пустая, т.к. для неё нужно 2+ месяца данных; структура готова принять их без
    # изменения схемы, когда данные появятся
    cohort_scaffold = pd.DataFrame(columns=[
        'cohort_month', 'activity_month', 'months_since_cohort', 'cohort_size', 'active_users', 'retention_pct'
    ])

    return {'day_n_curve': day_n_curve, 'monthly_repeat_rate': monthly, 'cohort_scaffold': cohort_scaffold}

def calc_top_products(unified: pd.DataFrame) -> pd.DataFrame:
    """
    Функция считает рейтинг всех товаров по продажам на основе purchase-событий:
    gmv, число заказов, число уникальных покупателей, средняя цена, и два ранга — по GMV и
    по числу заказов (см. комментарий ниже, почему они не совпадают и оба нужны).
    """
    purchases = unified[unified['event_name'] == 'purchase'].copy()
    # у purchase-строк product_id всегда заполнен (см. validate_null_patterns),
    # приводим к int - после join через unified колонка была float из-за NaN у view/click/add
    purchases['product_id'] = purchases['product_id'].astype(int)

    top = purchases.groupby('product_id').agg(
        gmv=('revenue', 'sum'),
        orders_cnt=('order_id', 'nunique'),
        buyers_cnt=('user_id', 'nunique'),
    ).reset_index()

    top['avg_price'] = (top['gmv'] / top['orders_cnt']).round(2)

    top = top.sort_values('gmv', ascending=False).reset_index(drop=True)
    top['rank_by_gmv'] = top.index + 1
    # method='min' - если у двух товаров одинаковое orders_cnt, у обоих будет одинаковый ранг
    # (а не произвольный порядок между ними)
    top['rank_by_orders'] = top['orders_cnt'].rank(method='min', ascending=False).astype(int)

    return top

def add_money_metrics(g: pd.DataFrame) -> pd.DataFrame:
    """
    Функция добавляет средний чек и среднее число заказов на пользователя к
    уже сгруппированной таблице с колонками gmv, orders_cnt, users_with_orders в
    функции calc_gmv_trend ниже.
    """
    g['avg_check'] = (g['gmv'] / g['orders_cnt']).round(2)
    g['avg_orders_per_user'] = (g['orders_cnt'] / g['users_with_orders']).round(2)

def calc_gmv_trend(unified: pd.DataFrame) -> dict:
    """
    Функция считает тренд GMV на основе purchase-событий из unified-таблицы:
    - daily: GMV и число заказов по дням
    - weekly: то же по неделям (неделя начинается с понедельника); последняя неделя отбрасывается,
      если она неполная (меньше 7 дней в пределах датасета) — иначе на графике она выглядела бы как
      обвал GMV, хотя это просто обрезанные данные, а не падение продаж.
    - monthly: то же по месяцам — сейчас одна строка (январь), структура готова копить данные по
      мере поступления новых месяцев.
    """
    purchases = unified[unified['event_name'] == 'purchase'].copy()
    purchases['date'] = purchases['datetime'].dt.normalize()
    # последняя дата в датасете — граница, по которой определяем полноту недели
    max_date = purchases['date'].max()

    daily = purchases.groupby('date').agg(
        gmv=('revenue', 'sum'), orders_cnt=('order_id', 'nunique'), users_with_orders=('user_id', 'nunique')
    ).reset_index().rename(columns={'date': 'period_start'})
    daily['period_type'] = 'day'
    add_money_metrics(daily)

    # начало недели (понедельник) для каждой даты — группировка по неделям
    purchases['week_start'] = purchases['date'] - pd.to_timedelta(purchases['date'].dt.dayofweek, unit='D')
    weekly = purchases.groupby('week_start').agg(
        gmv=('revenue', 'sum'), orders_cnt=('order_id', 'nunique'), users_with_orders=('user_id', 'nunique')
    ).reset_index().rename(columns={'week_start': 'period_start'})
    # оставляем только недели, у которых 7-й день (week_start + 6) не выходит
    # за пределы датасета — то есть неделя целиком покрыта данными
    weekly = weekly[weekly['period_start'] + pd.Timedelta(days=6) <= max_date].reset_index(drop=True)
    weekly['period_type'] = 'week'
    add_money_metrics(weekly)

    # начало месяца — задел под накопление нескольких месяцев в будущем
    purchases['month_start'] = purchases['date'].values.astype('datetime64[M]')
    monthly = purchases.groupby('month_start').agg(
        gmv=('revenue', 'sum'), orders_cnt=('order_id', 'nunique'), users_with_orders=('user_id', 'nunique')
    ).reset_index().rename(columns={'month_start': 'period_start'})
    monthly['period_type'] = 'month'
    add_money_metrics(monthly)

    mart_gmv_trend = pd.concat([daily, weekly, monthly], ignore_index=True, sort=False)
    cols = ['period_type', 'period_start', 'gmv', 'orders_cnt', 'users_with_orders', 'avg_check', 'avg_orders_per_user']
    return mart_gmv_trend[cols]
# Вызов функции:  mart_gmv_trend = calc_gmv_trend(unified)

def calc_click_without_add(unified: pd.DataFrame, session_window_minutes: int = 30) -> dict:
    """
    Функция считает долю кликов в карточку товара (pdp), которые НЕ привели к добавлению этого же
    товара в корзину — сигнал возможных проблем UX карточки товара (сходил, посмотрел, не добавил).

    Клик и add сопоставляются по паре (user_id, product_id) и по времени: ищется ближайший add после клика,
    не позже чем через session_window_minutes (иначе клик и add могут относиться к разным, никак не связанным
    визитам пользователя: без окна могут попасться совпадения с разрывом до нескольких дней).
    """
    pdp = unified[unified['page'] == 'pdp'].copy()

    clicks = pdp[pdp['event_name'] == 'click'][['user_id', 'product_id', 'datetime']].sort_values('datetime')
    adds = pdp[pdp['event_name'] == 'add'][['user_id', 'product_id', 'datetime']].sort_values('datetime')
    adds = adds.rename(columns={'datetime': 'add_datetime'})

    # merge_asof - специальный join для упорядоченных по времени данных:
    # ищет ближайшее значение в adds ПОСЛЕ (direction='forward') каждого клика,
    # отдельно в пределах каждой пары (user_id, product_id) - параметр by
    matched = pd.merge_asof(
        clicks, adds,
        left_on='datetime', right_on='add_datetime',
        by=['user_id', 'product_id'], direction='forward',
        tolerance=pd.Timedelta(minutes=session_window_minutes),
    )
    matched['converted_to_add'] = matched['add_datetime'].notna()

    # день клика - точка отсчёта для дневной агрегации
    matched['dt'] = matched['datetime'].dt.normalize()

    daily = matched.groupby('dt').agg(
        total_clicks=('converted_to_add', 'size'),
        clicks_with_add=('converted_to_add', 'sum'),
    ).reset_index()
    daily['clicks_with_add'] = daily['clicks_with_add'].astype(int)
    daily['clicks_without_add'] = daily['total_clicks'] - daily['clicks_with_add']
    daily['click_without_add_pct'] = (daily['clicks_without_add'] / daily['total_clicks'] * 100).round(1)

    return daily

def init_db(connection):
    """
    Функция Создаёт все 7 таблиц витрины в SQLite, если их ещё нет (IF NOT EXISTS - безопасно вызывать повторно,
    не перезатирает данные).
    CHECK-ограничения - вторая линия защиты поверх Python-валидации (validate_known_values, validate_no_nulls и т.д.):
    сработают, даже если данные попадут в БД в обход этих функций.
        """
    # Создаем курсор для выполнения SQL-запросов
    cur = connection.cursor()

    # SQL-запрос для создания таблицы , если она не существует
    cur.execute('''
            CREATE TABLE IF NOT EXISTS stag_unified_events (  -- создаем таблицу на основе unified
                event_dt       TEXT NOT NULL,
                user_id        INTEGER NOT NULL,
                event_name     TEXT NOT NULL CHECK (event_name IN ('view','click','add','purchase')),
                page           TEXT NOT NULL CHECK (page IN ('main_page','catalog','search','recommendations','pdp','cart')),
                product_id     INTEGER,
                order_id       INTEGER,
                revenue        REAL
            );
        ''')

    cur.execute('''
            CREATE TABLE IF NOT EXISTS mart_funnel (        -- таблица для рассчета воронки и конверсий по срезам
                dimension_type          TEXT NOT NULL CHECK (dimension_type IN ('overall','page')),
                dimension_value         TEXT NOT NULL,
                view_count              INTEGER NOT NULL CHECK (view_count >= 0),
                click_count             INTEGER NOT NULL CHECK (click_count >= 0),
                add_count               INTEGER NOT NULL CHECK (add_count >= 0),
                purchase_count          INTEGER NOT NULL CHECK (purchase_count >= 0),
                view_to_add_pct         REAL,
                click_to_add_pct        REAL,
                add_to_purchase_pct     REAL,
                view_to_purchase_pct    REAL,
                PRIMARY KEY (dimension_type, dimension_value)
            );
        ''')

    cur.execute('''
            CREATE TABLE IF NOT EXISTS mart_retention_day_n (   -- таблица с метриками удержания по n-дням
                day_offset       INTEGER NOT NULL,
                cohort_size      INTEGER NOT NULL CHECK (cohort_size >= 0),
                returned_users   INTEGER NOT NULL CHECK (returned_users >= 0),
                retention_pct    REAL,
                PRIMARY KEY (day_offset)
            );
        ''')

    cur.execute('''
            CREATE TABLE IF NOT EXISTS mart_retention_monthly_repeat (      -- таблица с метриками повторных покупок за месяц
                month_start        TEXT NOT NULL,
                total_buyers        INTEGER NOT NULL CHECK (total_buyers >= 0),
                repeat_buyers        INTEGER NOT NULL CHECK (repeat_buyers >= 0),
                repeat_rate_pct    REAL NOT NULL,
                PRIMARY KEY (month_start)
            );
        ''')

    cur.execute('''
            CREATE TABLE IF NOT EXISTS mart_gmv_trend (     -- таблица с метрик gmv с трендом по выбранному периоду
                period_type              TEXT NOT NULL CHECK (period_type IN ('day','week','month')),
                period_start             TEXT NOT NULL,
                gmv                      REAL NOT NULL CHECK (gmv >= 0),
                orders_cnt                INTEGER NOT NULL CHECK (orders_cnt >= 0),
                users_with_orders         INTEGER NOT NULL CHECK (users_with_orders >= 0),
                avg_check                 REAL NOT NULL,
                avg_orders_per_user      REAL NOT NULL,
                PRIMARY KEY (period_type, period_start)
            );
        ''')

    cur.execute('''
            CREATE TABLE IF NOT EXISTS mart_top_products (      -- таблица с рейтингом популярных продуктов
                product_id        INTEGER NOT NULL,
                gmv                REAL NOT NULL CHECK (gmv >= 0),
                orders_cnt        INTEGER NOT NULL CHECK (orders_cnt >= 0),
                buyers_cnt        INTEGER NOT NULL CHECK (buyers_cnt >= 0),
                avg_price         REAL NOT NULL,
                rank_by_gmv        INTEGER NOT NULL,
                rank_by_orders     INTEGER NOT NULL,
                PRIMARY KEY (product_id)
            );
        ''')

    cur.execute('''
            CREATE TABLE IF NOT EXISTS mart_click_without_add (     -- таблица рассчитывает долю кликов в карточку товара (pdp), которые затем не были добавлены в корзину
                dt                         TEXT NOT NULL,       -- дата
                total_clicks               INTEGER NOT NULL CHECK (total_clicks >= 0),
                clicks_with_add            INTEGER NOT NULL CHECK (clicks_with_add >= 0),
                clicks_without_add         INTEGER NOT NULL CHECK (clicks_without_add >= 0),
                click_without_add_pct      REAL NOT NULL,
                PRIMARY KEY (dt)
            );
        ''')

    #Подтверждаем изменения и записываем их в базу данных
    connection.commit()

def create_data_mart(engine, unified, mart_funnel, retention, mart_gmv_trend, top_products, click_without_add) -> None:
    """
    Загружает уже посчитанные метрики в таблицы витрины (созданные init_db).

    Аргументы:
    - engine: соединение с БД (sqlite3.Connection - функция работает через pandas.to_sql,
      который принимает и sqlite3.Connection, и SQLAlchemy engine одинаково)
    - unified: результат build_unified_events -> stg_unified_events
    - mart_funnel: результат calc_funnel_metrics -> mart_funnel
    - retention: словарь из calc_retention_metrics (day_n_curve, monthly_repeat_rate)
    - mart_gmv_trend: результат calc_gmv_trend -> mart_gmv_trend
    - top_products: результат calc_top_products -> mart_top_products
    - click_without_add: результат calc_click_without_add -> mart_click_without_add
    """
    tables = {
        'stag_unified_events': unified.rename(columns={'datetime': 'event_dt'})[
            ['event_dt', 'user_id', 'event_name', 'page', 'product_id', 'order_id', 'revenue']
        ],
        'mart_funnel': mart_funnel,
        'mart_retention_day_n': retention['day_n_curve'],
        'mart_retention_monthly_repeat': retention['monthly_repeat_rate'],
        'mart_gmv_trend': mart_gmv_trend,
        'mart_top_products': top_products,
        'mart_click_without_add': click_without_add,
    }

    cur = engine.cursor()
    for table_name, df in tables.items():
        # очищаем содержимое, но не структуру - CHECK/PRIMARY KEY из init_db
        # остаются нетронутыми, в отличие от to_sql(if_exists='replace')
        cur.execute(f"DELETE FROM {table_name}")
        df.to_sql(table_name, engine, if_exists='append', index=False)

    engine.commit()

# Создаем список с перечнем названия листов в будущем Excel файле
sheets = [
    'stag_unified_events', 'mart_funnel', 'mart_retention_day_n',
    'mart_retention_monthly_repeat', 'mart_gmv_trend', 'mart_top_products',
    'mart_click_without_add',
]
def export_to_excel(conn, excel_path: str) -> None:
    """
    Экспортирует все 7 таблиц витрины из SQLite в один Excel-файл - по листу на таблицу, имя листа совпадает
    с именем таблицы. Этот файл и читает DataLens как источник данных для дашборда.
    """

    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        for table_name in sheets:
            print(f"start {table_name}")
            df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
            sheet_name = table_name
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"End {table_name}")


#Пути к исходному и выходному файлам, а также к базе данных и вспомогательным элементам
input_file1 = '/opt/airflow/dags/vkusvill/events.csv'                  #загруженный файл о событиях с товарами
input_file2 = '/opt/airflow/dags/vkusvill/orders.csv'                  #загруженный файл о заказах
validated_events_path = '/opt/airflow/dags/vkusvill/validated_events.csv'
validated_orders_path = '/opt/airflow/dags/vkusvill/validated_orders.csv'
unified_metrics_path = '/opt/airflow/dags/vkusvill/unified_metrics_path.csv'
top_products_path = '/opt/airflow/dags/vkusvill/top_products_path.csv'
mart_funnel_path = '/opt/airflow/dags/vkusvill/mart_funnel.csv'
mart_gmv_trend_path = '/opt/airflow/dags/vkusvill/mart_gmv_trend.csv'
click_without_add_path = '/opt/airflow/dags/vkusvill/click_without_add.csv'
retention_day_n_path = '/opt/airflow/dags/vkusvill/retention_day_n.csv'
retention_monthly_path = '/opt/airflow/dags/vkusvill/retention_monthly.csv'
required_columns_events = ['datetime', 'user_id', 'event_name', 'page', 'product_id', 'order_id']   # поля файла events
required_columns_orders = ['datetime', 'user_id', 'product_id', 'order_id', 'revenue']  # поля файла orders
known_event_names = {'view', 'click', 'add', 'purchase'}    #set известных событий для ф-ции проверки их наличия в поле event_name
datalens_export_path = '/opt/airflow/dags/vkusvill/dl_export_vkusvill.xlsx'  #Файл сохраняем в таблицу Excel для Datalens

def extract_task():
    df_events = read_source_file(input_file1)
    df_orders = read_source_file(input_file2)

    validate_columns(df_events, required_columns_events)
    validate_columns(df_orders, required_columns_orders)

    validate_data_quality(df_events, df_orders)

    validate_datetime_column(df_events)
    validate_datetime_column(df_orders)

    orders = validate_no_duplicate_order_id(df_orders)
    purchase_events = df_events[df_events['event_name'] == 'purchase']
    validate_no_duplicate_order_id(purchase_events)

    events = validate_null_patterns(df_events)
    orders = validate_no_nulls(orders, required_cols=['user_id', 'product_id', 'order_id', 'revenue'])
    events = validate_known_values(events, column='event_name', allowed_values=known_event_names)

    events.to_csv(validated_events_path, index=False)
    orders.to_csv(validated_orders_path, index=False)

def transform_task_metrics():
    events = read_source_file(validated_events_path)
    orders = read_source_file(validated_orders_path)

    # csv не хранит dtype - после записи/чтения 'datetime' снова строка, конвертируем обратно
    validate_datetime_column(events)
    validate_datetime_column(orders)

    unified = build_unified_events(events, orders)
    mart_funnel = calc_funnel_metrics(unified)
    mart_gmv_trend = calc_gmv_trend(unified)
    retention = calc_retention_metrics(unified)
    top_products = calc_top_products(unified)
    click_without_add = calc_click_without_add(unified)

    unified.to_csv(unified_metrics_path, index=False)
    top_products.to_csv(top_products_path, index=False)
    mart_funnel.to_csv(mart_funnel_path, index=False)
    mart_gmv_trend.to_csv(mart_gmv_trend_path, index=False)
    click_without_add.to_csv(click_without_add_path, index=False)
    retention['day_n_curve'].to_csv(retention_day_n_path, index=False)
    retention['monthly_repeat_rate'].to_csv(retention_monthly_path, index=False)

def load_data_mart_task():
    unified = read_source_file(unified_metrics_path)
    top_products = read_source_file(top_products_path)
    mart_funnel = read_source_file(mart_funnel_path)
    mart_gmv_trend = read_source_file(mart_gmv_trend_path)
    click_without_add = read_source_file(click_without_add_path)
    retention = {
        'day_n_curve': read_source_file(retention_day_n_path),
        'monthly_repeat_rate': read_source_file(retention_monthly_path),
    }

    with sqlite3.connect('vkusvill_mart.db') as conn:
        init_db(conn)
        create_data_mart(conn, unified, mart_funnel, retention, mart_gmv_trend, top_products, click_without_add)
        export_to_excel(conn, datalens_export_path)

#Создаем DAG
dag_create = DAG(
    'vkusvill_file_processing_pipeline',            #Название пайплайна
    default_args=default_args,                      #Стандартные аргументы
    description='Пайплайн для обработки файла',     #Описание
    schedule="0 8 * * 1",                           # каждый понедельник в 08:00,
    start_date=datetime(2024, 2, 1),     #Начальная дата запуска
    catchup=False,                                  #Не выполнять пропущенные запуски
)

extract_op = PythonOperator(
    task_id='extract',
    python_callable=extract_task,
    dag=dag_create,
)
transform_op = PythonOperator(
    task_id='transform',
    python_callable=transform_task_metrics,
    dag=dag_create,
)
load_op = PythonOperator(
    task_id='load_data_mart',
    python_callable=load_data_mart_task,
    dag=dag_create,
)

extract_op >> transform_op >> load_op