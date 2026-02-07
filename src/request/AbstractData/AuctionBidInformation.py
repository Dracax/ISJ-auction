import dataclasses

from request.AbstractData.AbstractData import register_data_type, DataType, AbstractData


@register_data_type(DataType.AUCTION_BID_INFORMATION)
@dataclasses.dataclass
class AuctionBidInformation(AbstractData):
    auction_id: int
    name: str
    bidder: str
    bid_amount: float
    outbid: bool = False
