"""Шаг 3: запись data.inc для Rainmeter и обновление скина."""
import logging
import os
import subprocess
from pathlib import Path

from config import RAINMETER_EXE, SKIN_NAME

log = logging.getLogger(__name__)


def write_inc(variables: dict[str, str], path: Path) -> None:
    """Пишет файл вида [Variables] / Имя=Значение.

    Кодировка UTF-16 — иначе Rainmeter покажет кириллицу «кракозябрами».
    Сначала пишем во временный файл, потом подменяем: так Rainmeter
    никогда не прочитает наполовину записанный файл.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["[Variables]"] + [f"{name}={value}" for name, value in variables.items()]
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-16") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, path)


def refresh_skin() -> None:
    """Просит запущенный Rainmeter перечитать скин."""
    if not RAINMETER_EXE.exists():
        log.warning("Rainmeter не найден: %s", RAINMETER_EXE)
        return
    subprocess.run([str(RAINMETER_EXE), "!Refresh", SKIN_NAME], timeout=15)
