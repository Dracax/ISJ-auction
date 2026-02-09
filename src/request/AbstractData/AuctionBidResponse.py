from dataclasses import dataclass
from uuid import UUID

from request.AbstractData.AbstractData import register_data_type, DataType
from request.AbstractData.AbstractResponse import AbstractResponse


@register_data_type(DataType.AUCTION_BID_RESPONSE)
@dataclass
class AuctionBidResponse(AbstractResponse):
    bid_id: UUID  # id for the bid
    message: str
    name: str


@register_data_type(DataType.AUCTION_PLACE_RESPONSE)
@dataclass
class AuctionPlaceResponse(AbstractResponse):
    auction_id: int | None  # id for the auction
    message: str
