"""Общие настройки проекта.

Здесь только то, что не секретно. ID таблицы и названия листов
лежат в settings.json — он в .gitignore и на GitHub не попадает.
"""
import json
from pathlib import Path

# Папка проекта — от неё строим все пути, чтобы скрипт работал
# из любой рабочей папки (важно для Планировщика заданий)
BASE_DIR = Path(__file__).resolve().parent

CREDS_PATH = BASE_DIR / "credentials.json"
SETTINGS_PATH = BASE_DIR / "settings.json"
LOGS_DIR = BASE_DIR / "logs"
MAIN_SCRIPT = BASE_DIR / "main.py"
# pythonw.exe — тот же Python, но без чёрного окна консоли
PYTHONW = BASE_DIR / ".venv" / "Scripts" / "pythonw.exe"

# Доступ только на чтение и только к таблицам (без Google Диска)
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# Rainmeter
RAINMETER_EXE = Path(r"C:\Program Files\Rainmeter\Rainmeter.exe")
SKIN_NAME = "MenuWidget"
SKIN_DIR = Path.home() / "Documents" / "Rainmeter" / "Skins" / SKIN_NAME
INC_PATH = SKIN_DIR / "@Resources" / "data.inc"


def load_settings() -> dict:
    """Читает settings.json: spreadsheet_id и названия листов."""
    if not SETTINGS_PATH.exists():
        raise FileNotFoundError(
            f"Не найден {SETTINGS_PATH.name}. "
            "Скопируйте settings.example.json в settings.json и заполните."
        )
    with open(SETTINGS_PATH, encoding="utf-8") as f:
        return json.load(f)
