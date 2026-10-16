# \[English version](README\_EN.md)

# 

# Мониторинг курсов валют ЦБ РФ: автоматизированный ETL и дашборд

Прототип системы, которая каждый день забирает официальные курсы валют из API Банка России, хранит историю в PostgreSQL и показывает динамику и волатильность на интерактивном дашборде. Дипломный проект по программе «Аналитик данных».

**Дашборд:** [открыть в Yandex DataLens](https://datalens.ru/sq708osjqtn2b-izmenenie-kursa-valyut?state=19b2f8af56)

**Презентация и материалы проекта:** [Google Drive](https://drive.google.com/drive/folders/1OmD2XpXBJbA_mDRi9JtY9ShpE4Gxw-O1?usp=drive_link)

!\[Дашборд](images/dashboard.png)

\---

## Зачем это бизнесу

**Для кого.** Финансовый или закупочный отдел ритейлера, который закупает товары или оборудование за валюту (США, Евросоюз, Китай, Великобритания, Армения).

**Проблема.** Курс влияет на себестоимость импортных позиций. Когда курсы смотрят вручную на сайте, нет истории, нет сравнения валют между собой и нельзя сказать, в какой валюте риск выше.

**Что даёт дашборд.** Три ответа без ручной работы:

|Вопрос бизнеса|Что смотреть на дашборде|Какое решение это поддерживает|
|-|-|-|
|Куда движется курс?|График динамики и `% изменения за день`|Когда закупать, а когда подождать|
|В какой валюте риск выше?|Волатильность за 30 дней в процентах, одна шкала для всех валют|В какой валюте заключать контракт|
|Данным можно доверять?|Индикатор даты последней загрузки|Можно ли принимать решение по текущим цифрам|

Дашборд не прогнозирует курс и не считает экономию в рублях. Он даёт закупочному отделу основу для решения: историю, сравнение валют и оценку риска в одном месте.

\---

## Архитектура

!\[Архитектура](images/architecture.png)

```
API ЦБ РФ  →  Python (extract, transform)  →  Airflow DAG  →  PostgreSQL (Neon)  →  Yandex DataLens
```

|Компонент|Что делает|
|-|-|
|API ЦБ РФ (`XML\_daily.asp`)|Источник: официальные курсы, XML, без авторизации|
|Python (`requests`, `xml.etree`)|Забирает XML за нужную дату, приводит типы, считает курс за 1 единицу валюты|
|Apache Airflow 3 (Docker)|Запускает загрузку каждый день в 19:30 МСК, перезапуски и догрузка истории|
|PostgreSQL (Neon, облако)|Хранилище: справочник валют, факты курсов, SQL-вьюха с метриками|
|Yandex DataLens|Дашборд поверх вьюхи, фильтры по валюте и периоду|

Состав папки:

```
diploma/
├── cbr\_currency\_transform.py   # extract\_cbr\_rates, transform\_cbr\_rates (без зависимости от Airflow)
└── cbr\_currency\_etl.py         # DAG: расписание, задачи, запись в БД
```

Логика разделена на два файла сознательно. Функции работы с API ничего не знают про Airflow, поэтому их можно запускать и проверять отдельно.

\---

## Структура базы данных

Схема «измерение и факты»: `dim\_currency` хранит справочник, `fact\_exchange\_rate` хранит ежедневные наблюдения.

```sql
CREATE TABLE dim\_currency (
    currency\_id SERIAL PRIMARY KEY,
    char\_code   VARCHAR(3) NOT NULL UNIQUE,
    name        TEXT,
    is\_tracked  BOOLEAN NOT NULL DEFAULT false
);

CREATE TABLE fact\_exchange\_rate (
    rate\_id       SERIAL PRIMARY KEY,
    currency\_id   INT NOT NULL REFERENCES dim\_currency(currency\_id),
    rate\_date     DATE NOT NULL,
    nominal       INT NOT NULL,
    value         NUMERIC(10,4) NOT NULL,
    rate\_per\_unit NUMERIC(10,4) NOT NULL,
    loaded\_at     TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (currency\_id, rate\_date)
);
```

* `is\_tracked` задаётся вручную в базе и определяет, какие валюты загружает DAG. Чтобы добавить валюту, достаточно одной SQL-команды, код менять не нужно.
* `rate\_per\_unit = value / nominal`. ЦБ даёт курс за разный номинал (например, за 100 единиц), без приведения к «1 единице» валюты нельзя сравнивать.
* `UNIQUE (currency\_id, rate\_date)` делает загрузку идемпотентной: повторный запуск за ту же дату обновляет строку и не создаёт дубль.

Отслеживаемые валюты: USD, EUR, CNY, GBP, AMD.

\---

## Как работает DAG

`cbr\_exchange\_rates\_etl`, расписание `30 19 \* \* \*` (каждый день в 19:30 МСК, уже после публикации курса ЦБ).

```python
tracked\_codes = get\_tracked\_currencies\_task()
raw\_rates     = extract\_task()
transformed   = transform\_task(raw\_rates, tracked\_codes)
validate\_and\_load\_task(transformed, tracked\_codes)
```

1. `get\_tracked\_currencies\_task` читает из `dim\_currency` валюты с `is\_tracked = true`.
2. `extract\_task` берёт логическую дату запуска Airflow (`ds`), переводит её в формат ЦБ и забирает курсы за эту дату.
3. `transform\_task` оставляет нужные валюты и считает `rate\_per\_unit`.
4. `validate\_and\_load\_task` проверяет, что пришли все отслеживаемые валюты (иначе падает с понятной ошибкой), и записывает данные в БД.

Запись устроена как upsert:

```sql
INSERT INTO fact\_exchange\_rate
    (currency\_id, rate\_date, nominal, value, rate\_per\_unit, loaded\_at)
SELECT currency\_id, %(rate\_date)s, %(nominal)s, %(value)s, %(rate\_per\_unit)s, now()
FROM dim\_currency
WHERE char\_code = %(char\_code)s
ON CONFLICT (currency\_id, rate\_date)
DO UPDATE SET
    value = EXCLUDED.value,
    rate\_per\_unit = EXCLUDED.rate\_per\_unit,
    loaded\_at = EXCLUDED.loaded\_at;
```

Дата берётся из логической даты запуска, а не из текущего времени. Поэтому любой прошлый запуск можно перезапустить (`Clear` в Airflow), и он загрузит курс именно за свою дату. История с `start\_date = 2026-07-01` загружается автоматически благодаря `catchup=True`.

!\[DAG в Airflow](images/airflow\_dag.png)

\---

## Как считаются метрики

Метрики считаются в SQL-вьюхе `v\_exchange\_rate\_stats`, дашборд только показывает результат.

```sql
CREATE VIEW v\_exchange\_rate\_stats AS
WITH base AS (
    SELECT
        f.currency\_id,
        c.char\_code,
        f.rate\_date,
        f.rate\_per\_unit,
        ROUND(
            (f.rate\_per\_unit - LAG(f.rate\_per\_unit) OVER (PARTITION BY f.currency\_id ORDER BY f.rate\_date))
            / LAG(f.rate\_per\_unit) OVER (PARTITION BY f.currency\_id ORDER BY f.rate\_date) \* 100,
            4
        ) AS pct\_change\_1d
    FROM fact\_exchange\_rate f
    JOIN dim\_currency c ON c.currency\_id = f.currency\_id
)
SELECT
    currency\_id,
    char\_code,
    rate\_date,
    rate\_per\_unit,
    ROUND(
        STDDEV(pct\_change\_1d) OVER (
            PARTITION BY currency\_id ORDER BY rate\_date
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ),
        4
    ) AS volatility\_30d,
    pct\_change\_1d
FROM base;
```

|Поле|Что означает|
|-|-|
|`pct\_change\_1d`|На сколько процентов курс изменился по сравнению с предыдущим днём. Показывает направление и скорость|
|`volatility\_30d`|Стандартное отклонение дневных `% изменений` за 30 дней. Показывает, насколько курс скачет изо дня в день. Чем выше значение, тем выше риск|

**Почему волатильность считается по процентам, а не по цене.** Курсы сильно различаются по масштабу: GBP стоит около 117 ₽, AMD около 0,24 ₽. Разброс в рублях для них несопоставим. Разброс дневных процентных изменений сравним у любых валют.

Для первых строк истории `pct\_change\_1d` и `volatility\_30d` равны `NULL`, потому что сравнивать ещё не с чем.

\---

## Дашборд

Дашборд собран в Yandex DataLens на двух датасетах:

* `metrics\_ds` читает всю вьюху и нужен для графика динамики (важны все даты).
* `latest\_snapshot\_ds` отдаёт по одной последней строке на валюту. Нужен для таблицы сравнения и графика волатильности, чтобы не суммировать показатели по всем датам.

```sql
SELECT DISTINCT ON (currency\_id) \*
FROM v\_exchange\_rate\_stats
ORDER BY currency\_id, rate\_date DESC;
```

Что на дашборде:

* Блок с описанием: цель, источник данных, для кого.
* Индикаторы: дата последней загрузки, наименее волатильная валюта.
* График динамики курса по валютам.
* Таблица «на сегодня»: курс, изменение за день, волатильность.
* Столбчатая диаграмма волатильности за 30 дней.
* Фильтры по коду валюты и по периоду.

\---

## Как запустить

1. **База данных.** Создайте PostgreSQL. Для DataLens база должна быть доступна из интернета, поэтому использовалось облако Neon.
2. **Таблицы.** Выполните DDL из раздела выше, затем вьюху `v\_exchange\_rate\_stats`.
3. **Справочник валют:**

```sql
   INSERT INTO dim\_currency (char\_code, name, is\_tracked) VALUES
       ('USD', 'Доллар США', true),
       ('EUR', 'Евро', true),
       ('CNY', 'Юань', true),
       ('GBP', 'Фунт стерлингов', true),
       ('AMD', 'Армянский драм', true);
   ```

4. **Airflow.** Положите оба `.py` файла в папку `dags/diploma/`. В Airflow создайте Connection `diploma\_db` (тип Postgres, host, порт, база, логин, пароль) и в поле Extra укажите `{"sslmode": "require"}`.
5. **Запуск.** Включите DAG `cbr\_exchange\_rates\_etl`. С `start\_date = 2026-07-01` и `catchup=True` история загрузится автоматически.
6. **DataLens.** Создайте подключение к базе, затем датасеты на вьюхе и соберите чарты.

Пароли и строки подключения в репозиторий не коммитятся, они хранятся в Airflow Connection.

\---

## Технические заметки

* В Airflow 3.x папка `dags/` не добавляется в `PYTHONPATH` автоматически. Поэтому в начале DAG-файла путь добавляется вручную через `sys.path.insert`, иначе импорт `cbr\_currency\_transform` не работает.
* Зависимости между задачами строятся через передачу результатов (TaskFlow API), явные стрелки `>>` не нужны.
* `catchup=True` оставлен сознательно, чтобы история накапливалась и догонялась после пауз.

## Ограничения

* Airflow запущен в Docker на локальном компьютере, поэтому запуск по расписанию происходит, только если компьютер включён. Для постоянной работы систему нужно перенести на сервер.
* История данных небольшая, поэтому выводы о волатильности носят предварительный характер.
* Прогнозирование курса не входит в проект. Дашборд описывает прошлое и текущий риск.

## Стек

Python, Apache Airflow 3, PostgreSQL (Neon), SQL (оконные функции, CTE), Docker, Yandex DataLens.

