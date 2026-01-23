from dataclasses import dataclass

from request.AbstractData.AbstractData import register_data_type, DataType
from request.AbstractRequest import AbstractRequest


@register_data_type(DataType.AUCTION_RETRIEVE_REQUEST)
@dataclass
class AuctionRetrieveRequest(AbstractRequest):
    only_open: bool
