"""Точка входа: Google Таблица → data.inc → Rainmeter.

Запуск:
    python main.py               — обычный запуск (так его вызывает Планировщик)
    python main.py --no-refresh  — только записать data.inc, не трогая Rainmeter
"""
import logging
import sys
import time
from datetime import date
from logging.handlers import RotatingFileHandler

from google.auth.exceptions import TransportError
from requests.exceptions import ConnectionError, Timeout

from config import INC_PATH, LOGS_DIR, MAIN_SCRIPT, PYTHONW, load_settings
from export import refresh_skin, write_inc
from fetch import fetch_menu, fetch_sheet_urls, open_spreadsheet
from transform import build_widget_vars, parse_menu

log = logging.getLogger("widget")

# При входе в Windows или после сна сеть поднимается не сразу — даём ей время
ATTEMPTS = 3
RETRY_DELAY_SEC = 30
NETWORK_ERRORS = (ConnectionError, Timeout, TransportError)


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


def fetch_with_retry(settings: dict) -> tuple[list[list], dict[str, str]]:
    """Загрузка из Google; при сетевой ошибке — ещё попытки с паузой."""
    for attempt in range(1, ATTEMPTS + 1):
        try:
            sh = open_spreadsheet(settings["spreadsheet_id"])
            rows = fetch_menu(sh, settings["menu_sheet"])
            urls = fetch_sheet_urls(sh, {"Menu": settings["menu_sheet"], **settings["link_sheets"]})
            return rows, urls
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
        rows, urls = fetch_with_retry(settings)

        menu = parse_menu(rows)
        widget_vars = build_widget_vars(menu, urls, date.today())
        # Пути для кнопки ⟳ — чтобы скин не хранил их у себя
        widget_vars["PythonW"] = str(PYTHONW)
        widget_vars["MainScript"] = str(MAIN_SCRIPT)

        write_inc(widget_vars, INC_PATH)
        # В лог — только служебная информация, без названий блюд
        log.info("OK: дней в меню %d, меню до %s, записан %s",
                 len(menu), widget_vars["MenuUntil"], INC_PATH)
    except Exception:
        # Старый data.inc не трогаем — виджет покажет последние удачные данные
        log.exception("Ошибка обновления, data.inc не изменён")
        return 1

    if "--no-refresh" not in sys.argv:
        refresh_skin()
    return 0


if __name__ == "__main__":
    sys.exit(main())
