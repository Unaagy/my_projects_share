"""Шаг 1: загрузка событий из Google Календаря."""
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build

from config import CREDS_PATH, SCOPES


def build_service():
    creds = service_account.Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def fetch_events(service, calendars: list[dict], start: datetime, end: datetime) -> list[tuple[dict, dict]]:
    """Все события всех календарей за период: [(календарь из настроек, событие), ...].

    singleEvents=True — Google сам разворачивает повторяющиеся события
    («каждый вторник») в отдельные даты.
    """
    result = []
    for cal in calendars:
        page_token = None
        while True:  # событий может быть больше, чем помещается в один ответ
            resp = service.events().list(
                calendarId=cal["id"], timeMin=start.isoformat(), timeMax=end.isoformat(),
                singleEvents=True, maxResults=2500, pageToken=page_token,
            ).execute()
            result += [(cal, ev) for ev in resp.get("items", [])]
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
    return result


def fetch_event_colors(service) -> dict[str, str]:
    """Палитра цветов событий Google: {"11": "#dc2127", ...}."""
    palette = service.colors().get().execute()["event"]
    return {color_id: c["background"] for color_id, c in palette.items()}
