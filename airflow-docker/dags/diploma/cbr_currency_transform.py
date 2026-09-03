from datetime import datetime
import requests
# Превращение текстовой XML-строки в объект, по которому удобно ходить и доставать данные.
import xml.etree.ElementTree as ET

def extract_cbr_rates(date_req: str) -> list[dict]:
    """
    date_req: дата в формате 'DD/MM/YYYY' (формат ЦБ, в дальнейшем нужно преобразовать в формат 'YYYY/MM/DD')
    Возвращает сырой список словарей по всем валютам за эту дату.
    """
    url = "https://www.cbr.ru/scripts/XML_daily.asp"
    response = requests.get(url, params={"date_req": date_req}, timeout=10)
    response.encoding = "windows-1251"

    root = ET.fromstring(response.text)     # превращает XML-текст в объект-дерево; root — это корневой узел
    rate_date_raw = root.attrib["Date"]  # дата снапшота из самого ответа - "DD.MM.YYYY"
    rate_date = datetime.strptime(rate_date_raw, "%d.%m.%Y").strftime("%Y-%m-%d")  # преобразуем в "YYYY-MM-DD"

    rates = []
    for valute in root.findall("Valute"):
        rates.append({
            "char_code": valute.find("CharCode").text,
            "nominal": int(valute.find("Nominal").text),
            "value": float(valute.find("Value").text.replace(",", ".")),
            "rate_date": rate_date,
        })
    return rates


def transform_cbr_rates(raw_rates: list[dict], tracked_codes: list[str]) -> list[dict]:
    """
    raw_rates: сырой список от extract_cbr_rates (все >50 валют)
    tracked_codes: список char_code, нужных для анализа, например ["USD", "EUR", "CNY"]
    Возвращает только нужные валюты с добавленным полем rate_per_unit.
    """
    tracked_set = set(tracked_codes)   # преобразуем список в множество для более быстрого поиска валют в списке tracked_codes
    transformed = []

    for rate in raw_rates:
        if rate["char_code"] not in tracked_set:
            continue
        transformed.append({
            **rate,     # создаем независимую копию с добавленным полем (ключ - "rate_per_unit"), ничего не трогая в оригинале
            "rate_per_unit": round(rate["value"] / rate["nominal"], 4),
        })

    return transformed

if __name__ == "__main__":
    current_date = "24/08/2026"
    valute_list = extract_cbr_rates(current_date)
    print(len(valute_list))

    used_valutes = ["USD", "EUR", "CNY", "AMD", "GBP"]
    print(transform_cbr_rates(valute_list, used_valutes))