"""Загрузка колод из Google Таблицы и их локальная копия.

Копия (data/cards.json, в .gitignore) нужна, чтобы смена колоды и пересборка
очереди работали мгновенно и без интернета.
"""
import json
import os

from config import BASE_DIR, CREDS_PATH, SCOPES

CACHE_PATH = BASE_DIR / "data" / "cards.json"


def clean(value) -> str:
    """Убирает лишние пробелы и переносы строк внутри ячейки."""
    return " ".join(str(value).split())


def fetch_decks(spreadsheet_id: str, exclude: list[str]) -> list[dict]:
    """Все листы-колоды: [{"name", "gid", "cards": [[A, B], ...]}, ...].

    Первая строка листа — заголовок, пропускается. Берутся только строки,
    где заполнены оба столбца A и B.
    """
    # Импорт здесь, а не в начале файла: gspread загружается долго,
    # а answer.py (кнопки виджета) берёт из этого модуля только load_cache
    import gspread

    gc = gspread.service_account(filename=CREDS_PATH, scopes=SCOPES)
    sh = gc.open_by_key(spreadsheet_id)
    decks = []
    for ws in sh.worksheets():
        if ws.title in exclude:
            continue
        cards = []
        for row in ws.get_all_values()[1:]:
            a, b = (clean(c) for c in (row + ["", ""])[:2])
            if a and b:
                cards.append([a, b])
        decks.append({"name": ws.title, "gid": ws.id, "cards": cards})
    return decks


def save_cache(decks: list[dict]) -> None:
    CACHE_PATH.parent.mkdir(exist_ok=True)
    tmp = CACHE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(decks, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, CACHE_PATH)


def load_cache() -> list[dict]:
    if not CACHE_PATH.exists():
        raise FileNotFoundError("Нет локальной копии карточек — запустите python main.py (с интернетом)")
    return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
