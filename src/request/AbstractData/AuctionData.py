from dataclasses import dataclass
from typing import Optional


@dataclass
class AuctionData:
    auction_id: int
    item_name: str
    current_price: float
    starting_price: float
    current_bidder: Optional[str]  # Adress of Bidder, UIID of Bidder?
    item_owner: str  # Right data format?
