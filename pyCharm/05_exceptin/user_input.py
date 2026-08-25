class Math:

    def __init__(self, num1: str, num2: str):
        self.n1 = num1
        self.n2 = num2

    def zero_error(self):
        try:
            result = float(self.n1) / float(self.n2)
            return result
        except ZeroDivisionError as z:
            print("Ошибка деления на ноль")
            return None
        except ValueError as v:
            print("Введите числаl")
            return None


class NegativeNumberError(Exception):
    pass


def sqrt(number: str):
    try:
        if float(number) < 0:
            raise NegativeNumberError("Невозможно вычислить квадратный корень из отрицательного числа")
        return float(number) ** 0.5
    except ValueError:
        print(f"неверный формат ввода {number}, ожидается число")
    except NegativeNumberError as neg:
        print(neg)
    except Exception as e:
        print(e)
    finally:
        print("Операция завершена")


print("Введите первое число")
num1 = input()
print("Введите второе число")
num2 = input()
res = Math(num1, num2)
print(res.zero_error())

print("Введите число для вычисления его корня:")
n = input()
print(sqrt(n))
