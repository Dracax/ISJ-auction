from dataclasses import dataclass
from uuid import UUID

from request.AbstractData.AbstractClientRequest import AbstractClientRequest
from request.AbstractData.AbstractData import register_data_type, DataType


@register_data_type(DataType.ACUTION_PLACE)
@dataclass
class PlaceAuctionData(AbstractClientRequest):
    title: str
    starting_bid: float
    auction_owner: str
    owner_id: UUID
    notification_address: tuple[str, int]
