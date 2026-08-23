class Stack:

    def __init__(self, stack: list[str] = []):
        self.stack = stack

    def push(self, action: str):
        self.stack.append(action)

    def pop(self):
        if len(self.stack) == 0:
            print("Список пустой, заполните его")
        else:
            return self.stack.pop()

    def peek(self):
        if len(self.stack) == 0:
            print("Список пустой, заполните его")
        return self.stack[-1]

    def is_empty(self):
        if len(self.stack) == 0:
            return True
        else:
            return False


st = Stack()
st.push('внес')
st.push('banana')
st.push('пирог')
st.push('apple')
print(st.stack)
print(st.pop())
print(st.pop())
print(st.pop())
print(st.pop())
print(st.pop())
