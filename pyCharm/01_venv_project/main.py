import requests as re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

test_resp = re.get('https://restcountries.com/v3.1/all')
# print(test_resp.text)

df = pd.read_json(io.StringIO(test_resp.text))
df_table1 = df[['name', 'capital', 'languages', 'maps']]
df_table1 = df_table1.copy()
# print(df_table1)

#Вытаскиваем название страны
countries_list = []
for name in df_table1.name:
    list_common = name['common']
    countries_list.append(list_common)
# print(counties_list)

#создадим новую таблицу, в которой будет  'capital', 'languages' и присоеденим к ней name_country
df_clean = df_table1[['capital', 'languages']]
df_clean.loc.__setitem__((slice(None), 'name_country'), countries_list)
print(df_clean.sample(5))

########################################################
#Моя задача: вывести топ 10 используемых языков в мире по всем странам и написать в каких странах они используются

#создаюм функцию, которая создает чистый список всех языков из списка словарей
def flat_map (xs):
    ys = []
    for x in xs:
        ys.extend(list(x.values()))
    return ys

#создаем список из словарей, где нет nan
xs_list = list(df_clean['languages'].dropna())

#выводим список всех языко str в отработанной функции flat_map
flat_list = flat_map(xs_list)
# print(f'lang = {flat_list}')

#создаем функцию, которая считает количество стран, использующих каждый язык. Заносим данные в словарь
def group_and_count (flat_list):
    dict_language_count = {}
    for language in flat_list:
        one_val = 1
        if language not in dict_language_count.keys():
            dict_language_count[language] = one_val
        else:
            dict_language_count[language] += one_val
    return dict_language_count

#выводим словарь со счетчиком
count_group_dict = group_and_count(flat_list)
# print(f'dict from lang: {count_group_dict}')
print(f'1******************************************************')

#находим key с максимальным знаечнием value в словаре
max_key = max(count_group_dict, key=count_group_dict.get)
print(f'The most popular language is: {max_key}')

#сортируем языки в порядке убывания использования в странах
sort_language_dict = sorted(count_group_dict.items(), key = lambda x: x[1], reverse=True)

#создадим функцию, которая будет записывать в лист страны, говорящие на языке lang_name
print(f'>>> ******************************************************')
df_clean = df_clean.dropna()
lang_name = 'Russian'
def have_lang (lang_name):
    lang_county_list = []
    lang_list = []
    for i in df_clean.index:
        if lang_name in df_clean['languages'][i].values():
            lang_county_list.append(df_clean['name_country'][i])
    return lang_county_list

country_speaks = have_lang(lang_name)
print(f'Country speak in {str(lang_name)}: {country_speaks}')

#выводим топ 10 популярных языков и список стран, использующих эти языки
for i in sort_language_dict[0:10]:
    print(f'{i[0]}: {i[1]}: {have_lang(i[0])}\n')


#создаем визуализацию в matplotlib
x = [i[0] for i in sort_language_dict[0:10]]
y = [i[1] for i in sort_language_dict[0:10]]

fig = plt.figure(figsize=(10, 5))

bars = plt.bar(x, y, color='green', width=0.4)
plt.bar_label(bars)

plt.yticks(np.arange(0,100,10))
plt.xlabel('Languagies')
plt.ylabel('Countrys counts')
plt.title('Top 10 languagies in the world')
plt.show()

