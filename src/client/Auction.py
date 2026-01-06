import cmd

from client.AuctionServer import AuctionServer
from client.Person import Person


class AuctionShell(cmd.Cmd):
    intro = "Auction Shell. Tippe 'help' oder '?'. Mit 'exit' beenden."
    prompt = "auction> "

    def __init__(self):
        super().__init__()
        self.player: Person | None = None
        self.server = AuctionServer()

    def do_list(self, arg):
        "Listet offene Items: list"
        self.server.retrieve_auctions()

    def do_bid(self, arg):
        "Bietet auf ein Item: bid <item_id> <amount>"
        try:
            item_id_str, amount_str = arg.split()
            item_id = int(item_id_str)
            amount = float(amount_str)
            print(f"Gebot abgeben: Item {item_id}, Betrag {amount}")
        except ValueError:
            print("Usage: bid <item_id> <amount>")

    def do_post(self, arg):
        "Stellt ein neues Item ein: post <title> <start_price>"
        try:
            parts = arg.split()
            title = " ".join(parts[:-1])
            start_price = float(parts[-1])
            print(f"Item einstellen: {title} mit Startpreis {start_price}")
        except (ValueError, IndexError):
            print("Usage: post <title> <start_price>")

    def do_exit(self, arg):
        "Beendet die Shell"
        return True

    def start(self):
        print("Welcome to the auction game! Please enter your name to login.")
        name = input("Name: ")
        self.player = Person(name)
        print(f"Hello, {self.player.name}! You have successfully logged in.")
        self.cmdloop()


if __name__ == "__main__":
    AuctionShell().start()
