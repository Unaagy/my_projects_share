
class Queue:

    def __init__(self, queue: list[str] = []):
        self.queue = queue

    def enqueue(self, order: str):
        self.queue.append(order)

    def dequeue(self):
        if len(self.queue) == 0:
            print("Очередь пуста")
        else:
            return self.queue.pop(0)


    def is_empty(self):
        print(self.queue)
        if len(self.queue) == 0:
            return True
        return False

que = Queue()
que.enqueue('order1')
que.enqueue('order2')
que.enqueue('order3')
que.enqueue('order4')
print(que.queue)

order_to_process = que.dequeue()
print(order_to_process)

print(que.queue)

print(que.dequeue())
print(que.dequeue())
print(que.dequeue())
print(que.dequeue())
