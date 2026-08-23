
class Library:

    def __init__(self, books: list[str] = []):
        self.books = books

    def add_book(self, book_name: str):
        self.books.append(book_name)

    def remove_book(self, book_name: str):
        if book_name in self.books:
            self.books.remove(book_name)
        else:
            print(f"Книги с названием {book_name} не найдено")

    def display_books(self):
        if len(self.books) != 0:
            print(f"Список книг в библиотеке:")
            for book in self.books:
                print(f"{book}")
        else:
            print("Библиотека пуста")


b1 = Library(['том1', 'том2', 'том4'])
b1.add_book('том3')
b1.remove_book('том4')
b1.display_books()

