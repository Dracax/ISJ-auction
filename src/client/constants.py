from client.Item import Item
from client.Person import Person

POKEMON_CARD = Item("PokemonCard", "A card featuring a Pokemon character.")
KNIFE_ITEM = Item("Knife", "A sharp blade useful for cutting.")


SIMPLE_USER = Person("TestUser")
SIMPLE_USER.money = 1000
SIMPLE_USER.inventory.add_item(POKEMON_CARD, 5)
SIMPLE_USER.inventory.add_item(KNIFE_ITEM, 1)
