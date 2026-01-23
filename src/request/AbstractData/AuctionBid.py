from uuid import UUID
from dataclasses import dataclass
from typing import Optional

from request.AbstractData.AbstractData import AbstractData, register_data_type, DataType


@register_data_type(DataType.AUCTION_BID)
@dataclass
class AuctionBid(AbstractData):
    uuid: UUID
    auction_id: int
    bid: float
    name: str
