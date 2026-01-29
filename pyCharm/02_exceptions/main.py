#Напиши программу, которая принимает имя (путь к файлу) файла в качестве аргумента. Используй блок try-except, чтобы обработать
#случай, когда файл не существует. Выведи на экран количество строк в файле
import os.path as osp

TEST = 'C:\\Users\\Unaagy\\wdir\\learn\\productstar\\Test\\open_me.txt'


def get_file_content(file_path):
    cont = None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            cont = f.readlines()
    except Exception as ex:
        print(f'You have error: {ex}')
    return cont


if __name__ == '__main__':
    content = None
    while content is None:
        user_file_name = input('Write path to your file: ')
        print(f'Путь файла: {user_file_name}')
        content = get_file_content(osp.abspath(user_file_name))
    else:
        print(f'Кол-во строк в файле: {len(content)}')

