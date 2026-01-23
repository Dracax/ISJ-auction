from dataclasses import dataclass

from request.AbstractData.AbstractData import register_data_type, DataType, AbstractData
from request.AbstractData.AuctionData import AuctionData


@register_data_type(DataType.AUCTION_RETRIEVE_RESPONSE)
@dataclass
class RetrieveAuctionsResponse(AbstractData):
    auctions: list[AuctionData]
