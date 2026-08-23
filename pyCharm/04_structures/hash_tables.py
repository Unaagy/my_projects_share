
class HashTable:

    def __init__(self, n=10):
        self.lengh = n
        self.table = [[] for _ in range(n)]    # создаем массив фиксированного размера для хранения данных

    def remove(self, key):
        index = hash(key) % self.lengh
        tupl_to_remove = None
        for item in self.table[index]:
            if item[0] == key:
                tupl_to_remove = item
                break
        if tupl_to_remove:
            self.table[index].remove(tupl_to_remove)
            return True
        else:
            return False

    def insert(self, key: str, value: str):
        self.remove(key)
        index = hash(key) % self.lengh
        self.table[index].append((key, value))

    def get(self, key):
        index =hash(key) % self.lengh
        for val in self.table[index]:
            if key == val[0]:
                return val[1]
        return None





users = HashTable()
users.insert(1, "Vasja")
users.insert(2, "Sasha")
users.insert(3, "Masha")
users.insert(4, "Kay")
users.insert(13, "Katya")
users.insert(23, "Tya")
print(users.table)
users.insert(13, "Zoja")

print(users.table)



