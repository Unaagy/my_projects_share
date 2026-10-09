"""Точка входа: Google Календарь → data.inc → Rainmeter.

Запуск:
    python main.py               — обычный запуск (так его вызывает Планировщик)
    python main.py --no-refresh  — только записать data.inc, не трогая Rainmeter
"""
import logging
import sys
import time
from datetime import date, datetime, timedelta
from logging.handlers import RotatingFileHandler

from google.auth.exceptions import TransportError
from httplib2 import HttpLib2Error

from config import (DAYS_BACK, DAYS_FORWARD, INC_PATH, LOGS_DIR, MAIN_SCRIPT,
                    MAX_EVENTS, PYTHONW, load_settings)
from export import refresh_skin, write_inc
from fetch import build_service, fetch_event_colors, fetch_events
from transform import build_widget_vars, normalize

log = logging.getLogger("widget")

# При входе в Windows или после сна сеть поднимается не сразу — даём ей время
ATTEMPTS = 3
RETRY_DELAY_SEC = 30
# OSError покрывает обрывы соединения и таймауты
NETWORK_ERRORS = (OSError, HttpLib2Error, TransportError)


def setup_logging() -> None:
    """Лог в logs/widget.log (до 3 файлов по 200 КБ) и в консоль, если она есть.

    Под pythonw.exe (запуск из Планировщика) консоли нет, sys.stdout = None,
    поэтому print() там использовать нельзя — только логирование в файл.
    """
    LOGS_DIR.mkdir(exist_ok=True)
    handlers = [RotatingFileHandler(LOGS_DIR / "widget.log", maxBytes=200_000,
                                    backupCount=2, encoding="utf-8")]
    if sys.stdout:
        sys.stdout.reconfigure(encoding="utf-8")
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(level=logging.INFO, handlers=handlers,
                        format="%(asctime)s %(levelname)s %(message)s")


def fetch_with_retry(calendars: list[dict], start: datetime, end: datetime):
    """Загрузка из Google; при сетевой ошибке — ещё попытки с паузой."""
    for attempt in range(1, ATTEMPTS + 1):
        try:
            service = build_service()
            return fetch_events(service, calendars, start, end), fetch_event_colors(service)
        except NETWORK_ERRORS as e:
            if attempt == ATTEMPTS:
                raise
            log.warning("Нет сети (попытка %d из %d): %s. Жду %d с",
                        attempt, ATTEMPTS, type(e).__name__, RETRY_DELAY_SEC)
            time.sleep(RETRY_DELAY_SEC)


def main() -> int:
    setup_logging()
    try:
        settings = load_settings()
        today = date.today()
        # Границы периода — локальная полночь, с часовым поясом компьютера
        start = datetime.combine(today - timedelta(days=DAYS_BACK), datetime.min.time()).astimezone()
        end = datetime.combine(today + timedelta(days=DAYS_FORWARD + 1), datetime.min.time()).astimezone()

        pairs, google_colors = fetch_with_retry(settings["calendars"], start, end)
        events = normalize(pairs, settings.get("categories", []), google_colors)
        widget_vars = build_widget_vars(events, today, DAYS_BACK, DAYS_FORWARD, MAX_EVENTS,
                                        account=settings.get("google_account", ""))
        # Пути для кнопки ↻ — чтобы скин не хранил их у себя
        widget_vars["PythonW"] = str(PYTHONW)
        widget_vars["MainScript"] = str(MAIN_SCRIPT)

        write_inc(widget_vars, INC_PATH)
        # В лог — только служебная информация, без названий событий
        log.info("OK: событий %d за %d дн., сегодня %s, записан %s",
                 len(events), DAYS_BACK + DAYS_FORWARD + 1,
                 widget_vars[f"D{DAYS_BACK}Count"], INC_PATH)
    except Exception:
        # Старый data.inc не трогаем — виджет покажет последние удачные данные
        log.exception("Ошибка обновления, data.inc не изменён")
        return 1

    if "--no-refresh" not in sys.argv:
        refresh_skin()
    return 0


if __name__ == "__main__":
    sys.exit(main())
