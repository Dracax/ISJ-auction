from dataclasses import dataclass
from uuid import UUID

from request.AbstractData.AbstractData import register_data_type, DataType
from request.AbstractRequest import AbstractRequest


@register_data_type(DataType.ACUTION_PLACE)
@dataclass
class PlaceAuctionData(AbstractRequest):
    title: str
    starting_bid: float
    auction_owner: str
    owner_id: UUID
