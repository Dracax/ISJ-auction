from .Person import Person


class Auction:
    def __init__(self):
        self.player: Person | None = None

    def start(self):
        print("Welcome to the auction game! Please enter your name to login.")
        name = input("Name: ")
        self.player = Person(name)
        print(f"Hello, {self.player.name}! You have successfully logged in.")

        while True:
            pass
