import source.conditions as cond
import source.functions as func
import source.file_operations as flop
import source.json_util as js_u


if __name__ == '__main__':
    user_settings = js_u.load_from_json()
    print(f"Привет, {user_settings['user_name']}! Добро пожаловать в чат-бот!")

    conversation = []
    history = flop.load_conversation()

    print(f"Прочитано {len(history)} строк истории")

    while True:
        user_input = input()

        if user_input.lower() == "выход":
            print("Чат-бот: До свидания!")
            conversation = history + conversation
            flop.save_conversation(conversation)
            break

        greetings_response = cond.respond_to_greeting(user_input)

        if greetings_response != "Я тебя не понимаю":
            response = greetings_response
        else:
            response = func.chat_bot(user_input, user_settings)

        conversation.append(f"{user_settings['user_name']}: {user_input}\n")
        conversation.append(f"Чат-бот: {response}\n")

        print(f"Чат-бот: {response}")