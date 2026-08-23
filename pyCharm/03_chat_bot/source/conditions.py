# Функция для обработки ответа на сообщения пользователя
def respond_to_greeting(message):
    greetings = ["привет", "здравствуйте", "добрый день"]
    farewells = ["пока", "до свидания", "прощай"]

    if message.lower() in greetings:
        return "И тебе привет!"
    elif message.lower() in farewells:
        return "Давай прощаться!"
    else:
        return "Я тебя не понимаю"
