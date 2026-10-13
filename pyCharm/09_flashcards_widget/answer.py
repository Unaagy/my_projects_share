"""Запись ответа на карточку. Вызывается из Rainmeter по кнопкам:

    pythonw answer.py know  <номер колоды> <id карточки>   — «✓ Знаю»
    pythonw answer.py again <номер колоды> <id карточки>   — «✗ Не знаю» → повтор завтра

Только обновляет progress.json, скин не трогает: Rainmeter уже сам
перелистнул карточку и прибавил счётчик. Работает без интернета и
не импортирует gspread — чтобы запускаться как можно быстрее.
"""
import logging
import sys
from datetime import date
from logging.handlers import RotatingFileHandler

import progress
from config import LOGS_DIR
from fetch import load_cache

log = logging.getLogger("answer")


def main() -> int:
    LOGS_DIR.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[RotatingFileHandler(LOGS_DIR / "widget.log", maxBytes=200_000,
                                                      backupCount=2, encoding="utf-8")])
    try:
        action, deck_no, cid = sys.argv[1], int(sys.argv[2]), sys.argv[3]
        deck = load_cache()[deck_no - 1]["name"]
        with progress.locked():
            data = progress.load()
            saved = progress.record_answer(data, cid, deck, action, date.today())
            if saved:
                progress.save(data)
        # В лог — только служебное: действие и ID, без текста карточки
        log.info("answer %s %s: %s", action, cid, "записан" if saved else "уже был сегодня")
    except Exception:
        log.exception("Ошибка записи ответа: %s", sys.argv[1:])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
