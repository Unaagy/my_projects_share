
class Student:
    _DO_NOT_CHANGE = 1000000
    sex = "male"

    def __init__(self, name: str, second_name: str, age: int):
        self.name = name
        self.second_name = second_name
        self.age = age
        self.full_name = f"{name} {self.second_name}"

    def info(self):
        print(f"{self.name} {self.second_name}: {self.age} ({self.full_name}), {self.sex}")


if __name__ == '__main__':
    print("---")

    s1 = Student("Mark", "Volovic", 20,)
    s1.sex = "female"
    s1.info()



