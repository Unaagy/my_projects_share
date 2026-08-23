import random
import math
from source import json_util


# Функция генерации ответов на сообщение от пользователя
def chat_bot(message: str, user_settings: dict):
    response_dict = {
        "как дела": "У меня все хорошо, спасибо!",
        "что ты умеешь?": "Я могу отвечать на простые вопросы",
        "сколько будет 2 плюс 2": "2+2=4"
    }

    random_responses = ["Интересный вопрос!", "Я подумаю на этим...", "Давай поговорим о чем-нибудь другом"]

    unknown_answer = "Извините, я не знаю как ответить на это"

    response = response_dict.get(message.lower(), unknown_answer)

    math_operations = ["плюс", "минус", "умножить", "разделить", "степень",
                       "процент", "корень", "синус", "косинус", "тангенс"]

    binary_operations = {
        "плюс": lambda x, y: x + y,
        "минус": lambda x, y: x - y,
        "умножить": lambda x, y: x * y,
        "разделить": lambda x, y: x / y,
        "степень": lambda x, y: x ** y,
        "процент": lambda x, y: x / y * 100
    }

    unary_operations = {
        "корень": lambda x: math.sqrt(x),
        "синус": lambda x: math.sin(x),
        "косинус": lambda x: math.cos(x),
        "тангенс": lambda x: math.tan(x)
    }

    if message.lower().startswith("новое имя:"):
        new_name = message.split(":")[1]
        json_util.update_settings(new_name, update_dict=user_settings)

    if "сколько будет" in message.lower():

        parts = message.lower().split()

        for word in parts:
            index = parts.index(word)

            if word in binary_operations:
                try:
                    num1 = int(parts[index - 1])
                    num2 = int(parts[index + 1])
                    return f"Результат: {binary_operations[word](num1, num2)}"
                except IndexError:
                    return (f"Извините, я не могу обработать это выражение. Введите название операции "
                            f"из списка:\n {math_operations},\n а число до операции и после")
                except ValueError:
                    return "Ошибка: Введите числа цифрами"

            if word in unary_operations:
                try:
                    num1 = int(parts[index - 1])
                    return f"Результат: {unary_operations[word](num1)}"
                except IndexError:
                    return (f"Извините, я не могу обработать это выражение. Введите название операции "
                            f"из списка:\n {math_operations},\n а число до операции")
                except ValueError:
                    return "Ошибка: Введите число цифрой"

        return (f"Я не поняла, какую операцию нужно выполнить. Введите название операции "
                f"из списка:\n {math_operations},\n а число до операции и после(если используется 2 числа)")

    if response == unknown_answer:
        response = random.choice(random_responses)

    return response

