from src.client.Inventory import Inventory


class Person:
    def __init__(self, name: str):
        self.name: str = name
        self.money: int = 0

        self.inventory: Inventory = Inventory()
