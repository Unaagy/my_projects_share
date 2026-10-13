"""Прогресс изучения: progress.json (в .gitignore — это личные данные).

Структура:
{
  "ui":    {"deck": "Английский язык"},              — последняя выбранная колода
  "cards": {"<id>": {"deck": "...", "level": 0,        — ступень интервала (−1 — с начала)
                     "due": "2026-10-13",              — дата следующего показа
                     "first": "2026-10-12", "last": "2026-10-12"}},  — первый и последний ответ
  "log":   {"2026-10-12": {"Английский язык": {"know": 3, "again": 1}}}  — оценки за день
}
"""
import hashlib
import json
import os
import time
from contextlib import contextmanager
from datetime import date, timedelta

from config import INTERVALS, PROGRESS_PATH

LOCK_PATH = PROGRESS_PATH.with_suffix(".lock")
LOG_DAYS_KEPT = 60


def card_id(deck: str, front: str) -> str:
    """Постоянный ID карточки: колода + текст столбца A.

    Исправили перевод (столбец B) — прогресс сохранится;
    исправили само слово (A) — это уже новая карточка.
    """
    return hashlib.sha1(f"{deck}\x1f{front.lower()}".encode("utf-8")).hexdigest()[:12]


@contextmanager
def locked():
    """Не даём двум процессам писать progress.json одновременно (быстрые клики)."""
    for _ in range(100):
        try:
            fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            # «Зависший» замок старше 10 секунд — остался от упавшего процесса
            if time.time() - LOCK_PATH.stat().st_mtime > 10:
                LOCK_PATH.unlink(missing_ok=True)
            time.sleep(0.05)
    else:
        raise TimeoutError("progress.json занят другим процессом")
    try:
        yield
    finally:
        os.close(fd)
        LOCK_PATH.unlink(missing_ok=True)


def load() -> dict:
    if PROGRESS_PATH.exists():
        data = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
    else:
        data = {}
    for key in ("ui", "cards", "log"):
        data.setdefault(key, {})
    return data


def save(data: dict) -> None:
    # Старые дни в журнале не нужны — храним последние 60
    for day in sorted(data["log"])[:-LOG_DAYS_KEPT]:
        del data["log"][day]
    tmp = PROGRESS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, PROGRESS_PATH)


def day_counts(data: dict, deck: str, day: str) -> dict:
    """Счётчики колоды за день: {"know": N, "again": M}.

    Раньше в журнале хранилось только число «Знаю» — такие записи переводим в новый вид.
    """
    day_log = data["log"].setdefault(day, {})
    counts = day_log.get(deck, 0)
    if isinstance(counts, int):
        counts = day_log[deck] = {"know": counts, "again": 0}
    return counts


def record_answer(data: dict, cid: str, deck: str, action: str, today: date) -> bool:
    """«know» (✓ Знаю) — интервал на ступень выше; «again» (✗ Не знаю) — повтор завтра с начала.

    Повторный ответ на ту же карточку в тот же день игнорируется.
    Возвращает True, если ответ записан.
    """
    t = today.isoformat()
    card = data["cards"].setdefault(cid, {"deck": deck, "level": -1, "first": t})
    if card.get("last") == t:
        return False
    if action == "know":
        card["level"] = min(card["level"] + 1, len(INTERVALS) - 1)
        card["due"] = (today + timedelta(days=INTERVALS[card["level"]])).isoformat()
    elif action == "again":
        card["level"] = -1
        card["due"] = (today + timedelta(days=1)).isoformat()
    else:
        raise ValueError(f"Неизвестное действие: {action}")
    day_counts(data, deck, t)[action] += 1
    card["last"] = t
    return True


def today_counts(data: dict, deck: str, today: date) -> dict:
    """{"know": N, "again": M} за сегодня — без записи в data, если дня ещё нет."""
    counts = data["log"].get(today.isoformat(), {}).get(deck, {"know": 0, "again": 0})
    return {"know": counts, "again": 0} if isinstance(counts, int) else counts
