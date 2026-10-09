"""Список уникальных названий событий — помогает придумать ключевые слова категорий.

Пишет в data/titles.txt (папка data в .gitignore). В консоль названия не выводит.

Запуск:  python list_titles.py
"""
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build

from config import BASE_DIR, CREDS_PATH, DAYS_BACK, DAYS_FORWARD, SCOPES, load_settings


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    creds = service_account.Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    now = datetime.now(timezone.utc)

    titles = Counter()
    for cal in load_settings()["calendars"]:
        events = service.events().list(
            calendarId=cal["id"],
            timeMin=(now - timedelta(days=DAYS_BACK)).isoformat(),
            timeMax=(now + timedelta(days=DAYS_FORWARD)).isoformat(),
            singleEvents=True, maxResults=2500,
        ).execute().get("items", [])
        titles.update(f"{ev.get('summary', '(без названия)').strip()}   [{cal['name']}]"
                      for ev in events)

    out = BASE_DIR / "data" / "titles.txt"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("Сколько раз  Название   [календарь]\n")
        for title, count in titles.most_common():
            f.write(f"{count:>10}  {title}\n")
    print(f"Уникальных названий: {len(titles)}. Список: {out}")


if __name__ == "__main__":
    main()
