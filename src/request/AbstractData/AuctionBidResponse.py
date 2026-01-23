from dataclasses import dataclass
from uuid import UUID

from request.AbstractData.AbstractData import register_data_type, DataType, AbstractData


@register_data_type(DataType.AUCTION_BID_RESPONSE)
@dataclass
class AuctionBidResponse(AbstractData):
    bid_id: UUID  # id for the bid
    success: bool
    message: str | None = None
