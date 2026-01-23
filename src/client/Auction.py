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
            self.server.send_bid(item_id, amount, self.player.name)
            print(f"Gebot abgeben: Item {item_id}, Betrag {amount}")
        except ValueError:
            print("Usage: bid <item_id> <amount>")

    def do_post(self, arg):
        "Stellt ein neues Item ein: post <item_name> <starting_price>"
        try:
            parts = arg.split()
            item_name = " ".join(parts[:-1])
            starting_price = float(parts[-1])
            self.server.place_auction(item_name, starting_price, self.player.name)
            print(f"Item einstellen: {item_name} mit Startpreis {starting_price}")
        except (ValueError, IndexError):
            print("Usage: post <title> <start_price>")
    
    def do_sub(self, arg):
        "Abonniert Updates zu einer Auktion: sub <auction_id>"
        try:
            parts = arg.split()
            auction_id = int(parts[-1])
            self.server.subscribe_2_auction(auction_id)
            print(f"Auktion: {auction_id} wurde abonniert")
        except (ValueError, IndexError):
            print("Usage: sub <auction_id>")

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
