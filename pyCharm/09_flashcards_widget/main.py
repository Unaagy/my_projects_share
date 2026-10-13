"""Точка входа: Google Таблица + progress.json → data.inc → Rainmeter.

Запуск:
    python main.py                 — скачать колоды из таблицы (так вызывает Планировщик и кнопка ↻)
    python main.py --local         — пересобрать очередь из локальной копии, без интернета
    python main.py --deck 2        — сделать текущей колоду №2 (вместе с --local — смена колоды на виджете)
    python main.py --no-refresh    — только записать data.inc, не трогая Rainmeter
    python main.py --local --settle — то же, что --local, но сначала подождать 0,8 с, пока
                                      answer.py запишет ответ на последнюю карточку
"""
import logging
import sys
import time
from datetime import date
from logging.handlers import RotatingFileHandler

from google.auth.exceptions import TransportError
from requests.exceptions import ConnectionError, Timeout

import progress
from config import INC_PATH, LOGS_DIR, MAIN_SCRIPT, PYTHONW, BASE_DIR, load_settings
from export import refresh_skin, write_inc
from fetch import fetch_decks, load_cache, save_cache
from transform import build_widget_vars

log = logging.getLogger("widget")

# При входе в Windows или после сна сеть поднимается не сразу — даём ей время
ATTEMPTS = 3
RETRY_DELAY_SEC = 30
NETWORK_ERRORS = (ConnectionError, Timeout, TransportError)
NEW_PER_DAY_DEFAULT = 20
SETTLE_SEC = 0.8


def setup_logging() -> None:
    """Лог в logs/widget.log (до 3 файлов по 200 КБ) и в консоль, если она есть.

    Под pythonw.exe (запуск из Планировщика и Rainmeter) консоли нет,
    sys.stdout = None, поэтому print() там использовать нельзя.
    """
    LOGS_DIR.mkdir(exist_ok=True)
    handlers = [RotatingFileHandler(LOGS_DIR / "widget.log", maxBytes=200_000,
                                    backupCount=2, encoding="utf-8")]
    if sys.stdout:
        sys.stdout.reconfigure(encoding="utf-8")
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(level=logging.INFO, handlers=handlers,
                        format="%(asctime)s %(levelname)s %(message)s")


def fetch_with_retry(settings: dict) -> list[dict]:
    """Загрузка из Google; при сетевой ошибке — ещё попытки с паузой."""
    for attempt in range(1, ATTEMPTS + 1):
        try:
            return fetch_decks(settings["spreadsheet_id"], settings.get("exclude_sheets", []))
        except NETWORK_ERRORS as e:
            if attempt == ATTEMPTS:
                raise
            log.warning("Нет сети (попытка %d из %d): %s. Жду %d с",
                        attempt, ATTEMPTS, type(e).__name__, RETRY_DELAY_SEC)
            time.sleep(RETRY_DELAY_SEC)


def arg_value(name: str) -> str | None:
    """Значение ключа командной строки: --deck 2 → "2"."""
    if name in sys.argv:
        i = sys.argv.index(name)
        return sys.argv[i + 1] if i + 1 < len(sys.argv) else None
    return None


def main() -> int:
    setup_logging()
    try:
        settings = load_settings()
        today = date.today()
        local = "--local" in sys.argv
        if "--settle" in sys.argv:
            time.sleep(SETTLE_SEC)

        decks = load_cache() if local else fetch_with_retry(settings)
        if not decks:
            raise ValueError("В таблице нет ни одного листа-колоды")
        if not local:
            save_cache(decks)

        with progress.locked():
            data = progress.load()
            # Текущая колода: из --deck, иначе последняя выбранная, иначе первая
            names = [d["name"] for d in decks]
            deck_arg = arg_value("--deck")
            if deck_arg and deck_arg.isdigit() and 1 <= int(deck_arg) <= len(decks):
                data["ui"]["deck"] = names[int(deck_arg) - 1]
                progress.save(data)
            current = names.index(data["ui"]["deck"]) if data["ui"].get("deck") in names else 0

        widget_vars = build_widget_vars(
            decks, current, data, today,
            new_per_day=int(settings.get("new_per_day", NEW_PER_DAY_DEFAULT)),
            spreadsheet_id=settings["spreadsheet_id"],
            account=settings.get("google_account", ""),
        )
        # Пути для кнопок — чтобы скин не хранил их у себя
        widget_vars["PythonW"] = str(PYTHONW)
        widget_vars["MainScript"] = str(MAIN_SCRIPT)
        widget_vars["AnswerScript"] = str(BASE_DIR / "answer.py")

        write_inc(widget_vars, INC_PATH)
        # В лог — только служебная информация, без слов
        log.info("OK%s: колод %d, текущая №%d, карточек %s, на сегодня %s, сегодня ✓%s ✗%s",
                 " (local)" if local else "", len(decks), current + 1,
                 widget_vars[f"Deck{current + 1}Total"], widget_vars["QLen"], widget_vars["TodayKnown"], widget_vars["TodayUnknown"])
    except Exception:
        # Старый data.inc не трогаем — виджет покажет последние удачные данные
        log.exception("Ошибка обновления, data.inc не изменён")
        return 1

    if "--no-refresh" not in sys.argv:
        refresh_skin()
    return 0


if __name__ == "__main__":
    sys.exit(main())
