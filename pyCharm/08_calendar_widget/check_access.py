"""Проверка доступа к Google Календарям.

Показывает только служебную информацию (название календаря, часовой пояс,
сколько событий в диапазоне), сами события не выводит.

Запуск:  python check_access.py
"""
import json
import sys
from datetime import datetime, timedelta, timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import CREDS_PATH, DAYS_BACK, DAYS_FORWARD, SCOPES, load_settings


def main() -> int:
    # Консоль Windows может быть не в UTF-8 — без этого кириллица и ✓/✗ падают с ошибкой
    sys.stdout.reconfigure(encoding="utf-8")

    # 1. Ключ сервисного аккаунта
    if not CREDS_PATH.exists():
        print(f"[1/3] ✗ Не найден {CREDS_PATH.name} в папке проекта.")
        return 1
    with open(CREDS_PATH, encoding="utf-8") as f:
        sa_email = json.load(f).get("client_email", "?")
    print(f"[1/3] ✓ Ключ найден. Сервисный аккаунт: {sa_email}")

    # 2. Настройки
    try:
        calendars = load_settings()["calendars"]
    except FileNotFoundError as e:
        print(f"[2/3] ✗ {e}")
        return 1
    print(f"[2/3] ✓ Настройки прочитаны, календарей в списке: {len(calendars)}")

    # 3. Каждый календарь: метаданные и количество событий в диапазоне
    creds = service_account.Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    now = datetime.now(timezone.utc)
    time_min = (now - timedelta(days=DAYS_BACK)).isoformat()
    time_max = (now + timedelta(days=DAYS_FORWARD)).isoformat()

    ok = True
    for cal in calendars:
        name = cal["name"]
        try:
            meta = service.calendars().get(calendarId=cal["id"]).execute()
            events = service.events().list(
                calendarId=cal["id"], timeMin=time_min, timeMax=time_max,
                singleEvents=True, maxResults=2500,
            ).execute().get("items", [])
        except HttpError as e:
            ok = False
            if e.resp.status == 404:
                print(f"[3/3] ✗ «{name}»: не найден. Проверьте ID и что календарь "
                      f"открыт для {sa_email}.")
            elif e.resp.status == 403 and "accessNotConfigured" in str(e.content):
                print(f"[3/3] ✗ «{name}»: в Google Cloud не включён Google Calendar API "
                      "(если только что включили — подождите 2–5 минут).")
            elif e.resp.status == 403:
                print(f"[3/3] ✗ «{name}»: нет доступа (403). Проверьте права "
                      f"для {sa_email} в настройках календаря.")
            else:
                print(f"[3/3] ✗ «{name}»: ошибка API {e.resp.status}: {e.reason}")
            continue

        colored = sum(1 for ev in events if "colorId" in ev)
        all_day = sum(1 for ev in events if "date" in ev.get("start", {}))
        print(f"[3/3] ✓ «{name}»: часовой пояс {meta.get('timeZone')}, "
              f"событий за −{DAYS_BACK}…+{DAYS_FORWARD} дн.: {len(events)} "
              f"(из них с цветом: {colored}, на весь день: {all_day})")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
