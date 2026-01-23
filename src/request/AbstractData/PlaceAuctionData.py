from dataclasses import dataclass
from uuid import UUID

from request.AbstractData.AbstractData import register_data_type, DataType, AbstractData


@register_data_type(DataType.ACUTION_PLACE)
@dataclass
class PlaceAuctionData(AbstractData):
    title: str
    starting_bid: float
    auction_owner: str
    owner_id: UUID
