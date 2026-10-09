"""Шаг 2: события → категории и цвета → переменные для виджета по дням."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
          "августа", "сентября", "октября", "ноября", "декабря"]
WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
RELATIVE = {-1: "Вчера", 0: "Сегодня", 1: "Завтра"}


@dataclass
class Event:
    title: str
    color: str          # "R,G,B" для Rainmeter
    all_day: bool
    start: datetime     # для событий на весь день — полночь первого дня
    end: datetime       # не включительно, как в Google


def clean(value) -> str:
    """Убирает лишние пробелы и переносы; «#» заменяет — в Rainmeter это переменная."""
    return " ".join(str(value).split()).replace("#", "＃")


def hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    return ",".join(str(int(h[i:i + 2], 16)) for i in (0, 2, 4))


def pick_color(ev: dict, cal: dict, categories: list[dict], google_colors: dict[str, str]) -> str:
    """Цвет события по схеме: цвет из Google → ключевые слова → цвет календаря."""
    if ev.get("colorId") in google_colors:
        return hex_to_rgb(google_colors[ev["colorId"]])
    title = ev.get("summary", "").lower()
    for cat in categories:  # первая подходящая категория побеждает
        if any(kw.strip().lower() in title for kw in cat["keywords"] if kw.strip()):
            return cat["color"]
    return cal["color"]


def to_local(value: dict) -> tuple[datetime, bool]:
    """Начало/конец события → (локальное время, на весь день ли).

    У обычных событий Google присылает dateTime с часовым поясом,
    у событий на весь день — только date.
    """
    if "dateTime" in value:
        return datetime.fromisoformat(value["dateTime"]).astimezone(), False
    d = date.fromisoformat(value["date"])
    return datetime.combine(d, time.min).astimezone(), True


def normalize(pairs: list[tuple[dict, dict]], categories: list[dict],
              google_colors: dict[str, str]) -> list[Event]:
    events = []
    for cal, ev in pairs:
        if ev.get("status") == "cancelled":
            continue
        start, all_day = to_local(ev["start"])
        end, _ = to_local(ev["end"])
        events.append(Event(
            title=clean(ev.get("summary", "(без названия)")),
            color=pick_color(ev, cal, categories, google_colors),
            all_day=all_day, start=start, end=end,
        ))
    return events


def time_label(ev: Event, day_start: datetime, day_end: datetime) -> str:
    """«09:00–10:00», «весь день»; «…» — если событие начинается вчера или кончается завтра."""
    if ev.all_day:
        return "весь день"
    left = ev.start.strftime("%H:%M") if ev.start >= day_start else "…"
    if ev.end == ev.start:
        return left
    right = ev.end.strftime("%H:%M") if ev.end <= day_end else "…"
    return f"{left}–{right}"


def events_for_day(events: list[Event], d: date) -> list[tuple[str, str, str]]:
    """События, которые идут в этот день: [(время, название, цвет), ...].

    Сначала события на весь день, потом по времени начала.
    """
    day_start = datetime.combine(d, time.min).astimezone()
    day_end = datetime.combine(d + timedelta(days=1), time.min).astimezone()
    todays = [ev for ev in events
              if (ev.start < day_end and ev.end > day_start)
              or (ev.start == ev.end and day_start <= ev.start < day_end)]
    todays.sort(key=lambda ev: (not ev.all_day, ev.start, ev.title))
    return [(time_label(ev, day_start, day_end), ev.title, ev.color) for ev in todays]


def format_day(d: date) -> str:
    return f"{WEEKDAYS[d.weekday()]}, {d.day} {MONTHS[d.month - 1]}"


def build_widget_vars(events: list[Event], today: date, days_back: int,
                      days_forward: int, max_events: int, account: str = "") -> dict[str, str]:
    """Плоский словарь переменных для Rainmeter.

    Дни нумеруются с 0 (самый ранний) — в именах переменных Rainmeter
    нельзя использовать минус. TodayIndex — номер сегодняшнего дня.
    account — адрес Google-аккаунта: ссылки откроются именно под ним,
    даже если в браузере выполнен вход в несколько аккаунтов.
    """
    authuser = f"?authuser={account}" if account else ""
    result = {"TodayIndex": str(days_back),
              "LastIndex": str(days_back + days_forward),
              "MaxEvents": str(max_events)}
    for i in range(days_back + days_forward + 1):
        offset = i - days_back
        d = today + timedelta(days=offset)
        day_events = events_for_day(events, d)
        shown = day_events[:max_events]

        rel = RELATIVE.get(offset)
        result[f"D{i}Title"] = f"{rel} · {format_day(d)}" if rel else format_day(d)
        result[f"D{i}URL"] = f"https://calendar.google.com/calendar/r/day/{d.year}/{d.month}/{d.day}{authuser}"
        result[f"D{i}Count"] = str(len(shown))
        hidden = len(day_events) - len(shown)
        result[f"D{i}More"] = f"+ ещё {hidden}" if hidden else ""
        result[f"D{i}HasMore"] = "1" if hidden else "0"   # Rainmeter не умеет сравнивать строки
        for j in range(1, max_events + 1):
            label, title, color = shown[j - 1] if j <= len(shown) else ("", "", "0,0,0")
            result[f"D{i}E{j}Time"] = label
            result[f"D{i}E{j}Text"] = title
            result[f"D{i}E{j}Color"] = color

    result["LastUpdate"] = datetime.now().strftime("%d.%m %H:%M")
    return result
