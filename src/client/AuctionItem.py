from dataclasses import dataclass

from client.AuctionOwner import AuctionOwner
from client.Item import Item


@dataclass
class AuctionItem:
    author: AuctionOwner
    item_id: int
    item: Item
    starting_price: int
    current_price: int
