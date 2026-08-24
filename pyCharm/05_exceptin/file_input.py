filename = input("Введите имя файла для чтения: ")

try:
    with open(filename, 'r', encoding='utf-8') as file:
        content = file.read()
except FileNotFoundError:
    print(f"Ошибка: файл {filename} не найден")
except PermissionError:
    print(f"Ошибка: нет прав доступа к файлу {filename}")
except Exception as e:
    print(f"Произошла какая-то ошибка {e}")
finally:
    print("Работа завершена")