"""Очередь карточек на сегодня и переменные для Rainmeter."""
import random
from datetime import date

from progress import card_id, today_counts


def for_rainmeter(text: str) -> str:
    """«#» в Rainmeter — начало переменной, заменяем на похожий символ."""
    return text.replace("#", "＃")


def oriented(cid: str, a: str, b: str, today: date) -> tuple[str, str]:
    """Случайная сторона вопроса: A→B или B→A.

    Случайность «с зерном» (ID карточки + дата): в течение дня карточка
    всегда показывается одной стороной, даже после обновлений.
    """
    flip = random.Random(f"{today}-{cid}").random() < 0.5
    return (b, a) if flip else (a, b)


# Размер шрифта вопроса по длине: слово — крупно, длинное определение — мельче
FONT_SIZES = [(30, 16), (80, 14)]   # до 30 символов — 16, до 80 — 14
FONT_SIZE_LONG = 12                 # длиннее — 12


def question_font_size(text: str) -> int:
    return next((size for limit, size in FONT_SIZES if len(text) <= limit), FONT_SIZE_LONG)


def build_queue(deck: dict, progress: dict, today: date, new_per_day: int) -> list[tuple[str, str, str]]:
    """Карточки на сегодня: [(id, вопрос, ответ), ...].

    - повторения: карточки, у которых подошла дата (due ≤ сегодня);
    - новые: ещё не отвеченные ни разу, по порядку строк в таблице,
      не больше new_per_day в день (уже начатые сегодня учитываются);
    - отвеченные сегодня не попадают (их due — завтра или позже).
    Порядок случайный, но одинаковый в течение дня.
    """
    t = today.isoformat()
    cards = progress["cards"]
    started_today = sum(1 for c in cards.values() if c.get("first") == t and c.get("deck") == deck["name"])
    new_left = max(new_per_day - started_today, 0)

    queue = []
    for a, b in deck["cards"]:
        cid = card_id(deck["name"], a)
        rec = cards.get(cid)
        if rec is None:
            if new_left == 0:
                continue
            new_left -= 1
        elif rec.get("last") == t or rec.get("due", t) > t:
            continue
        queue.append((cid, *oriented(cid, a, b, today)))

    # Не shuffle: он раскладывает список заново, если в нём стало меньше карточек.
    # У каждой карточки свой «случайный номер на сегодня» — порядок оставшихся
    # не меняется, когда отвеченные уходят из очереди.
    queue.sort(key=lambda card: random.Random(f"{today}-{card[0]}").random())
    return queue


def build_practice(deck: dict, today: date) -> list[tuple[str, str, str]]:
    """«Пройти ещё раз»: вся колода в случайном порядке (на интервалы не влияет)."""
    queue = []
    for a, b in deck["cards"]:
        cid = card_id(deck["name"], a)
        queue.append((cid, *oriented(cid, a, b, today)))
    queue.sort(key=lambda card: random.Random(f"practice-{today}-{card[0]}").random())
    return queue


def deck_url(spreadsheet_id: str, gid: int, account: str) -> str:
    """Ссылка сразу на лист колоды; «?», а не «#» — «#» в Rainmeter занят."""
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit?gid={gid}"
    return url + (f"&authuser={account}" if account else "")


def build_widget_vars(decks: list[dict], current: int, progress: dict, today: date,
                      new_per_day: int, spreadsheet_id: str, account: str) -> dict[str, str]:
    """Плоский словарь для data.inc. Колоды нумеруются с 1; очередь — только текущей колоды."""
    result = {"DeckCount": str(len(decks)), "CurrentDeck": str(current + 1)}
    for n, deck in enumerate(decks, start=1):
        result[f"Deck{n}Name"] = for_rainmeter(deck["name"])
        result[f"Deck{n}Total"] = str(len(deck["cards"]))
        result[f"Deck{n}URL"] = deck_url(spreadsheet_id, deck["gid"], account)

    deck = decks[current]
    counts = today_counts(progress, deck["name"], today)
    result["TodayKnown"] = str(counts["know"])
    result["TodayUnknown"] = str(counts["again"])
    for prefix, queue in (("Q", build_queue(deck, progress, today, new_per_day)),
                          ("P", build_practice(deck, today))):
        result[f"{prefix}Len"] = str(len(queue))
        for k, (cid, front, back) in enumerate(queue, start=1):
            result[f"{prefix}{k}Id"] = cid
            result[f"{prefix}{k}Front"] = for_rainmeter(front)
            result[f"{prefix}{k}Back"] = for_rainmeter(back)
            result[f"{prefix}{k}Size"] = str(question_font_size(front))
    return result
