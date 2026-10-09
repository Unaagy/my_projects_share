"""Вымышленное меню для скриншотов: python main.py --demo.

Данные в том же формате, что приходят из Google Таблицы, поэтому
проходят через тот же transform.py и выглядят на виджете как настоящие.
"""
from datetime import date, timedelta

from transform import SHEETS_EPOCH

MEALS = ["Завтрак", "Обед", "Ужин"]
DISHES = [
    ["Овсянка с ягодами и мёдом", "Куриный суп с лапшой", "Запечённый лосось с овощами"],
    ["Сырники со сметаной", "Борщ и ржаной хлеб", "Паста с грибами и сливочным соусом"],
    ["Омлет с помидорами и зеленью", "Плов с говядиной", "Тёплый салат с киноа и тыквой"],
    ["Гранола с йогуртом", "Чечевичный суп", "Индейка с рисом и брокколи"],
]
# Ссылки кнопок ведут на главную Google Таблиц, а не на настоящую таблицу
DEMO_URL = "https://docs.google.com/spreadsheets"


def demo_menu(today: date) -> tuple[list[list], dict[str, str]]:
    """Строки как в листе «Меню» (дата числом, объединённые ячейки) и ссылки."""
    rows = [["Дата", "Время приема пищи", "Меню"]]
    for offset in range(-1, 6):
        serial = (today + timedelta(days=offset) - SHEETS_EPOCH).days
        dishes = DISHES[offset % len(DISHES)]
        for i, (meal, dish) in enumerate(zip(MEALS, dishes)):
            rows.append([serial if i == 0 else "", meal, dish])
    return rows, {"Menu": DEMO_URL, "Stock": DEMO_URL, "Shopping": DEMO_URL}
