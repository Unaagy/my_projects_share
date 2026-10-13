"""Проверка доступа к таблице с карточками.

Показывает только структуру: листы-колоды и количество карточек в них.
Сами слова и переводы не выводит.

Запуск:  python check_access.py
"""
import json
import sys
from collections import Counter

import gspread
from gspread.exceptions import APIError, SpreadsheetNotFound

from config import CREDS_PATH, RAINMETER_EXE, SCOPES, load_settings


def main() -> int:
    # Консоль Windows может быть не в UTF-8 — без этого кириллица и ✓/✗ падают с ошибкой
    sys.stdout.reconfigure(encoding="utf-8")

    # 1. Ключ сервисного аккаунта
    if not CREDS_PATH.exists():
        print(f"[1/4] ✗ Не найден {CREDS_PATH.name} в папке проекта.")
        return 1
    with open(CREDS_PATH, encoding="utf-8") as f:
        sa_email = json.load(f).get("client_email", "?")
    print(f"[1/4] ✓ Ключ найден. Сервисный аккаунт: {sa_email}")

    # 2. Настройки
    try:
        settings = load_settings()
    except FileNotFoundError as e:
        print(f"[2/4] ✗ {e}")
        return 1
    excluded = set(settings.get("exclude_sheets", []))
    print(f"[2/4] ✓ Настройки прочитаны. Исключённых листов: {len(excluded)}")

    # 3. Таблица
    gc = gspread.service_account(filename=CREDS_PATH, scopes=SCOPES)
    try:
        sh = gc.open_by_key(settings["spreadsheet_id"])
        worksheets = sh.worksheets()
    except SpreadsheetNotFound:
        print(f"[3/4] ✗ Таблица не найдена. Проверьте spreadsheet_id и что она открыта для {sa_email}.")
        return 1
    except APIError as e:
        print(f"[3/4] ✗ Ошибка доступа {e.response.status_code}. Таблица открыта для {sa_email}? "
              "Включён ли Google Sheets API?")
        return 1
    print(f"[3/4] ✓ Таблица открыта, листов: {len(worksheets)}")

    # 4. Колоды: только количества
    for ws in worksheets:
        if ws.title in excluded:
            print(f"[4/4] – «{ws.title}»: исключён в настройках")
            continue
        rows = ws.get_all_values()[1:]  # первая строка — заголовок
        rows = [(r + ["", ""])[:2] for r in rows]
        full = [(a.strip(), b.strip()) for a, b in rows if a.strip() and b.strip()]
        half = sum(1 for a, b in rows if bool(a.strip()) != bool(b.strip()))
        dups = sum(n - 1 for n in Counter(a.lower() for a, _ in full).values() if n > 1)
        extra = sum(1 for r in ws.get_all_values()[1:] if any(c.strip() for c in r[2:]))
        print(f"[4/4] ✓ «{ws.title}»: карточек {len(full)}"
              + (f", заполнена только одна сторона: {half}" if half else "")
              + (f", повторов в столбце A: {dups}" if dups else "")
              + (f", строк с данными правее столбца B (будут проигнорированы): {extra}" if extra else ""))

    print(f"\nRainmeter: {RAINMETER_EXE} {'✓' if RAINMETER_EXE.exists() else '✗ не найден'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
