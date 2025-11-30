from src.client.Item import Item


class Inventory:
    def __init__(self):
        self.items: dict[Item, int] = {}

    def add_item(self, item: Item, quantity=1):
        if item in self.items:
            self.items[item] += quantity
        else:
            self.items[item] = quantity

    def remove_item(self, item: Item, quantity=1):
        if item in self.items:
            if self.items[item] >= quantity:
                self.items[item] -= quantity
                if self.items[item] == 0:
                    del self.items[item]
            else:
                raise ValueError("Not enough items to remove")
        else:
            raise KeyError("Item not found in inventory")

    def get_quantity(self, item: Item):
        return self.items.get(item, 0)

    def list_items(self):
        return self.items.values()
