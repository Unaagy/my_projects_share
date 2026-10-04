"""Шаг 2: превращаем строки листа в переменные для виджета."""
import logging
from datetime import date, datetime, timedelta

log = logging.getLogger(__name__)

# С этой даты Google Таблицы отсчитывают дни: число 46300 = 05.10.2026
SHEETS_EPOCH = date(1899, 12, 30)

MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
          "августа", "сентября", "октября", "ноября", "декабря"]
WEEKDAYS = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
DAYS_TO_SHOW = [(-1, "Вчера"), (0, "Сегодня"), (1, "Завтра")]


def clean(value) -> str:
    """Убирает пробелы по краям и переносы строк внутри ячейки.

    «#» заменяем на похожий символ: в Rainmeter #...# — это переменная.
    """
    text = " ".join(str(value).split())
    return text.replace("#", "＃")


def parse_menu(rows: list[list]) -> dict[date, list[tuple[str, str]]]:
    """{дата: [(приём пищи, блюдо), ...]}.

    Дата стоит только в первой строке дня (ячейки объединены),
    поэтому запоминаем её и «протягиваем» на следующие строки.
    """
    menu: dict[date, list[tuple[str, str]]] = {}
    current = None
    for row_num, row in enumerate(rows[1:], start=2):  # строка 1 — заголовки
        row = list(row) + [""] * 3                      # API обрезает пустые ячейки справа
        raw_date, meal, dish = row[0], clean(row[1]), clean(row[2])

        if isinstance(raw_date, (int, float)):
            current = SHEETS_EPOCH + timedelta(days=int(raw_date))
        elif clean(raw_date):
            log.warning("Строка %d: в столбце «Дата» не дата — пропускаю день", row_num)
            current = None

        if current and (meal or dish):
            menu.setdefault(current, []).append((meal, dish))
    return menu


def format_day(d: date) -> str:
    return f"{d.day} {MONTHS[d.month - 1]}, {WEEKDAYS[d.weekday()]}"


def build_widget_vars(menu: dict, urls: dict[str, str], today: date) -> dict[str, str]:
    """Плоский словарь {имя переменной: строка} — так его понимает Rainmeter."""
    result = {}
    for n, (offset, label) in enumerate(DAYS_TO_SHOW, start=1):
        d = today + timedelta(days=offset)
        meals = menu.get(d)
        result[f"Day{n}Title"] = f"{label} · {format_day(d)}"
        # #CRLF# — перенос строки внутри текста в Rainmeter
        result[f"Day{n}Text"] = (
            "#CRLF#".join(f"{meal}: {dish or '—'}" for meal, dish in meals)
            if meals else "Меню не составлено"
        )

    result["MenuUntil"] = format_day(max(menu)) if menu else "—"
    for key, url in urls.items():
        result[f"{key}URL"] = url
    result["LastUpdate"] = datetime.now().strftime("%d.%m %H:%M")
    return result
