from dataclasses import dataclass
from typing import Optional

from request.AbstractData.AbstractData import AbstractData, register_data_type, DataType


@register_data_type(DataType.AUCTION)
@dataclass
class AuctionData(AbstractData):
    auction_id: int
    item_name: str
    current_price: float
    starting_price: float
    current_bidder: Optional[str] #Adress of Bidder, UIID of Bidder?
    item_owner: str #Right data format?
