def input_file(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()
            return content
    except FileNotFoundError:
        print(f"Ошибка: файл {filename} не найден")
    except PermissionError:
        print(f"Ошибка: нет прав доступа к файлу {filename}")
    except Exception as e:
        print(f"Произошла какая-то ошибка {e}")
    finally:
        print("Работа завершена")


filename = input("Введите имя файла для чтения: ")
text = input_file(filename)
print('-' * 50)
print(text)