from dataclasses import dataclass
from uuid import UUID

from request.AbstractData.AbstractClientRequest import AbstractClientRequest
from request.AbstractData.AbstractData import register_data_type, DataType


@register_data_type(DataType.AUCTION_BID)
@dataclass
class AuctionBid(AbstractClientRequest):
    uuid: UUID
    bid_id: UUID  # id for the bid will be send back in response
    auction_id: int
    bid: float
    name: str
