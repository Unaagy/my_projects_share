# \[English version](README\_EN.md)



# Bank of Russia Exchange Rate Monitoring: automated ETL and dashboard

A prototype system that downloads official exchange rates from the Bank of Russia API every day, stores the history in PostgreSQL, and shows trends and volatility on an interactive dashboard. Diploma project for the Data Analyst program.

[Русская версия](README.md) has the full SQL code and setup steps.

**Dashboard:** [Yandex DataLens](https://datalens.ru/sq708osjqtn2b-izmenenie-kursa-valyut?state=19b2f8af56) (the interface is in Russian)

**Presentation and project materials:** [Google Drive](https://drive.google.com/drive/folders/1OmD2XpXBJbA_mDRi9JtY9ShpE4Gxw-O1?usp=drive_link) (in Russian)

!\[Dashboard](images/dashboard.png)

\---

## Business value

**Who it is for.** A finance or procurement team of a retailer that buys goods or equipment in foreign currency (USD, EUR, CNY, GBP, AMD).

**The problem.** The exchange rate changes the cost of imported goods. Checking rates by hand gives no history, no comparison between currencies, and no answer to the question: which currency is riskier?

**What the dashboard answers:**

|Business question|What to look at|Decision it supports|
|-|-|-|
|Where is the rate heading?|Rate chart and daily % change|When to buy and when to wait|
|Which currency is riskier?|30-day volatility in %, one scale for all currencies|Which currency to use in a contract|
|Can I trust the data?|Last load date indicator|Whether the numbers are fresh|

The dashboard does not forecast rates and does not calculate savings in rubles. It gives the team a base for decisions: history, comparison between currencies, and a risk estimate in one place.

\---

## Architecture

!\[Architecture](images/architecture.png)

```
Bank of Russia API  →  Python (extract, transform)  →  Airflow DAG  →  PostgreSQL (Neon)  →  Yandex DataLens
```

|Component|Role|
|-|-|
|Bank of Russia API|Source: official rates, XML, no authorization|
|Python|Downloads rates for a date, converts types, calculates the rate per 1 unit of currency|
|Apache Airflow 3 (Docker)|Runs the load every day at 19:30 Moscow time, supports reruns and history backfill|
|PostgreSQL (Neon, cloud)|Storage: currency list, rate facts, SQL view with metrics|
|Yandex DataLens|Dashboard on top of the view, filters by currency and period|

Files in this folder:

```
diploma/
├── cbr\\\_currency\\\_transform.py   # extract and transform functions (no Airflow dependency)
└── cbr\\\_currency\\\_etl.py         # the DAG: schedule, tasks, database load
```

\---

## Data model

Two tables: `dim\\\_currency` (list of currencies, with an `is\\\_tracked` flag) and `fact\\\_exchange\\\_rate` (one row per currency per day). A unique key on `(currency\\\_id, rate\\\_date)` makes the load safe to rerun: a repeated run for the same date updates the row and does not create a duplicate.

`rate\\\_per\\\_unit = value / nominal`. The Bank of Russia gives some rates per 100 units, so rates must be converted to "per 1 unit" before they can be compared.

\---

## How the DAG works

`cbr\\\_exchange\\\_rates\\\_etl` runs every day at 19:30 Moscow time, after the daily rate publication.

1. Read the tracked currencies from `dim\\\_currency`.
2. Download the rates for the run's logical date.
3. Keep the tracked currencies and calculate `rate\\\_per\\\_unit`.
4. Check that all tracked currencies arrived (the task fails with a clear error if not), then write the data with an upsert.

The date comes from the logical date of the Airflow run, not from the current time. So any past run can be cleared and rerun, and it will load the rate for its own date. History from 2026-07-01 is loaded automatically with `catchup=True`.

!\[DAG in Airflow](images/airflow\_dag.png)

\---

## Metrics

Metrics are calculated in the SQL view `v\\\_exchange\\\_rate\\\_stats`. The dashboard only displays the result.

* `pct\\\_change\\\_1d`: percentage change of the rate compared with the previous day.
* `volatility\\\_30d`: standard deviation of daily percentage changes over the last 30 days. A higher value means a riskier currency.

**Why volatility is based on percentages, not on price.** Currencies have very different scales: GBP is about 117 RUB, AMD is about 0.24 RUB. Price spread in rubles cannot be compared between them. Spread of daily percentage changes can.

\---

## Dashboard

Built in Yandex DataLens on two datasets: one with the full history (for the trend chart) and one with only the latest row per currency (for the comparison table and the volatility chart, so values are not summed over all dates).

It includes: a description block (goal, data source, audience), two indicators (last load date, least volatile currency), a rate trend chart, a comparison table, a volatility bar chart, and filters by currency and period.

\---

## Limitations

* Airflow runs in Docker on a local computer, so scheduled runs happen only when the computer is on. A permanent setup needs a server.
* The history is short, so conclusions about volatility are preliminary.
* Forecasting is out of scope. The dashboard describes the past and the current risk.

## Stack

Python, Apache Airflow 3, PostgreSQL (Neon), SQL (window functions, CTE), Docker, Yandex DataLens.

