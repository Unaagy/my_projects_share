def save_conversation(conversation, filename="conversation.txt"):
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            for line in conversation:
                if line.strip():
                    file.write(line)
    except IOError as e:
        print(f"Ошибка при создании файла: {e}")

def load_conversation(filename="conversation.txt"):
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return file.readlines()
    except FileNotFoundError:
        print("Файл не найден.")
        return []