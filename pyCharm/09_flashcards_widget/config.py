"""Общие настройки проекта.

Здесь только то, что не секретно. ID таблицы и адрес аккаунта лежат
в settings.json — он в .gitignore и на GitHub не попадает.
Пути не привязаны к конкретному компьютеру: проект можно перенести на другой ПК.
"""
import json
import os
import winreg
from pathlib import Path

# Папка проекта — от неё строим все пути, чтобы скрипт работал
# из любой рабочей папки (важно для Планировщика заданий)
BASE_DIR = Path(__file__).resolve().parent

CREDS_PATH = BASE_DIR / "credentials.json"
SETTINGS_PATH = BASE_DIR / "settings.json"
PROGRESS_PATH = BASE_DIR / "progress.json"
LOGS_DIR = BASE_DIR / "logs"
MAIN_SCRIPT = BASE_DIR / "main.py"
# pythonw.exe — тот же Python, но без чёрного окна консоли
PYTHONW = BASE_DIR / ".venv" / "Scripts" / "pythonw.exe"

# Доступ только на чтение и только к таблицам
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# Интервалы повторения после «Знаю», в днях: 1 → 3 → 7 → 30
INTERVALS = [1, 3, 7, 30]

# Rainmeter. Скин лежит в проекте, а в папке скинов Rainmeter — ссылка на него
SKIN_NAME = "FlashcardsWidget"
SKIN_DIR = BASE_DIR / "rainmeter" / SKIN_NAME
INC_PATH = SKIN_DIR / "@Resources" / "data.inc"


def find_rainmeter_exe() -> Path:
    """Путь к Rainmeter.exe: из реестра (его пишет установщик), иначе — стандартный."""
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Rainmeter") as key:
            return Path(winreg.QueryValueEx(key, "")[0]) / "Rainmeter.exe"
    except OSError:
        return Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Rainmeter" / "Rainmeter.exe"


RAINMETER_EXE = find_rainmeter_exe()


def load_settings() -> dict:
    """Читает settings.json: ID таблицы, аккаунт, исключённые листы."""
    if not SETTINGS_PATH.exists():
        raise FileNotFoundError(
            f"Не найден {SETTINGS_PATH.name}. "
            "Скопируйте settings.example.json в settings.json и заполните."
        )
    with open(SETTINGS_PATH, encoding="utf-8-sig") as f:
        return json.load(f)
