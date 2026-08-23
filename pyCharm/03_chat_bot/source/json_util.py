import json as js

default_user_setting = {'user_name': 'Гость'}


def save_to_json(user_dict: dict):
    try:
        if len(user_dict) != 0:
            with open('users_settings.json', 'w', encoding='utf-8') as file:
                js.dump(user_dict, file, indent=4)
    except FileNotFoundError:
        print("Ошибка загрузки json в файл")


def load_from_json(json_file='users_settings.json') -> dict:
    try:
        with open(json_file, 'r', encoding='utf-8') as file:
            loaded_dict = js.load(file)
            if len(loaded_dict) == 0:
                loaded_dict = default_user_setting
            return loaded_dict
    except FileNotFoundError:
        return default_user_setting.copy()


def update_settings(new_value: str, update_dict: dict, key: str = "user_name"):
    update_dict[key] = new_value
    save_to_json(update_dict)


if __name__ == '__main__':
    user_setting_dict = load_from_json()
    print(f"{user_setting_dict['user_name']}")


    user_setting_dict['user_name'] = 'new name'
    print(default_user_setting)
    print(user_setting_dict)

    save_to_json(user_setting_dict)

    user_setting_dict["user_name"] = "Vasya"
    update_settings("fuck", user_setting_dict)
    print(user_setting_dict)


