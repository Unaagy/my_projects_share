"""Вымышленные события для скриншотов: python main.py --demo.

Данные в том же формате, что приходят из Google Календаря, поэтому
проходят через тот же transform.py и выглядят на виджете как настоящие.
"""
from datetime import date, datetime, time, timedelta

CALENDARS = {
    "main": {"name": "Основной", "color": "120,190,255"},
    "family": {"name": "Семейный", "color": "230,110,170"},
}
CATEGORIES = [
    {"name": "Здоровье", "color": "192,202,51", "keywords": ["йога", "окулист", "пробежка"]},
    {"name": "Работа", "color": "121,134,203", "keywords": ["созвон", "планёрка", "отчёт"]},
    {"name": "Дом", "color": "244,81,30", "keywords": ["уборка", "продукты", "ремонт"]},
    {"name": "Отдых", "color": "240,120,190", "keywords": ["кино", "ресторан"]},
    {"name": "Дети", "color": "246,191,38", "keywords": ["школ", "кружок", "детск"]},
]
# (смещение от сегодня, календарь, начало, конец, название); начало None — весь день
EVENTS = [
    (-1, "main", "09:00", "10:00", "Созвон с командой"),
    (-1, "main", "18:30", "19:30", "Йога"),
    (-1, "family", "19:30", "20:30", "Продукты на неделю"),
    (0, "family", None, None, "День рождения бабушки"),
    (0, "main", "07:30", "08:15", "Утренняя пробежка"),
    (0, "main", "10:00", "11:00", "Планёрка"),
    (0, "family", "13:00", "14:00", "Забрать детей из школы"),
    (0, "main", "15:30", "16:30", "Окулист"),
    (0, "family", "17:00", "18:00", "Кружок рисования"),
    (0, "main", "19:00", "21:00", "Ужин в ресторане"),
    (1, "main", "11:00", "12:00", "Отчёт за месяц"),
    (1, "family", "12:00", "14:00", "Генеральная уборка"),
    (1, "family", "18:00", "20:00", "Кино всей семьёй"),
    (2, "main", "09:30", "10:30", "Созвон с клиентом"),
    (2, "family", "16:00", "17:00", "Детский праздник"),
]


def _iso(d: date, hhmm: str) -> str:
    h, m = map(int, hhmm.split(":"))
    return datetime.combine(d, time(h, m)).astimezone().isoformat()


def demo_calendar(today: date) -> tuple[list[tuple[dict, dict]], list[dict]]:
    """Пары (календарь, событие) в формате Google API и категории."""
    pairs = []
    for offset, cal_key, start, end, title in EVENTS:
        d = today + timedelta(days=offset)
        if start is None:
            ev = {"summary": title, "start": {"date": d.isoformat()},
                  "end": {"date": (d + timedelta(days=1)).isoformat()}}
        else:
            ev = {"summary": title, "start": {"dateTime": _iso(d, start)},
                  "end": {"dateTime": _iso(d, end)}}
        pairs.append((CALENDARS[cal_key], ev))
    return pairs, CATEGORIES
