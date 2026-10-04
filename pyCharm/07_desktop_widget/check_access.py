"""Проверка доступа к Google Таблице.

Показывает только структуру (листы, заголовки, число строк),
сами значения не выводит.

Запуск:  python check_access.py
"""
import json
import sys

import gspread
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound

from config import CREDS_PATH, SCOPES, load_settings


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
    sheet_names = [settings["menu_sheet"], *settings["link_sheets"].values()]
    print(f"[2/4] ✓ Настройки прочитаны, листов для проверки: {len(sheet_names)}")

    # 3. Подключение к таблице
    gc = gspread.service_account(filename=CREDS_PATH, scopes=SCOPES)
    try:
        sh = gc.open_by_key(settings["spreadsheet_id"])
        all_titles = [ws.title for ws in sh.worksheets()]
    except SpreadsheetNotFound:
        print("[3/4] ✗ Таблица не найдена. Проверьте spreadsheet_id "
              f"и что таблица открыта для {sa_email}.")
        return 1
    except APIError as e:
        status = e.response.status_code
        if status == 403:
            print("[3/4] ✗ Нет доступа (403). Либо не включён Google Sheets API, "
                  f"либо таблица не открыта для {sa_email}.")
        else:
            print(f"[3/4] ✗ Ошибка API {status}: {e}")
        return 1
    print(f"[3/4] ✓ Таблица открыта. Все листы в ней: {all_titles}")

    # 4. Листы из настроек: только структура, без значений
    ok = True
    for name in sheet_names:
        try:
            ws = sh.worksheet(name)
        except WorksheetNotFound:
            print(f"[4/4] ✗ Лист «{name}» не найден (регистр и пробелы важны).")
            ok = False
            continue
        rows = ws.get_all_values()
        headers = rows[0] if rows else []
        print(f"[4/4] ✓ «{name}»: строк данных {max(len(rows) - 1, 0)}, "
              f"столбцы: {headers}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
