"""Шаг 1: загрузка данных из Google Таблицы."""
import gspread
from gspread.utils import ValueRenderOption

from config import CREDS_PATH, SCOPES


def open_spreadsheet(spreadsheet_id: str) -> gspread.Spreadsheet:
    gc = gspread.service_account(filename=CREDS_PATH, scopes=SCOPES)
    return gc.open_by_key(spreadsheet_id)


def fetch_menu(sh: gspread.Spreadsheet, sheet_name: str) -> list[list]:
    """Все строки листа «Меню».

    UNFORMATTED — значит, даты приходят числом (дни с 30.12.1899),
    а не текстом «5 октября»: так в них есть год и их легко сравнивать.
    """
    return sh.worksheet(sheet_name).get(value_render_option=ValueRenderOption.unformatted)


def fetch_sheet_urls(sh: gspread.Spreadsheet, link_sheets: dict[str, str]) -> dict[str, str]:
    """Ссылки, открывающие сразу нужный лист: {"Stock": "https://...?gid=..."}.

    Именно ?gid=, а не #gid=: в Rainmeter «#» обозначает переменную.
    """
    gids = {ws.title: ws.id for ws in sh.worksheets()}
    base = f"https://docs.google.com/spreadsheets/d/{sh.id}/edit?gid="
    return {key: base + str(gids[title]) for key, title in link_sheets.items()}
