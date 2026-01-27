from dataclasses import dataclass
from uuid import UUID

from request.AbstractData.AbstractData import register_data_type, DataType
from request.AbstractData.AbstractMulticastData import AbstractMulticastData


@register_data_type(DataType.MULTICAST_NEW_AUCTION)
@dataclass
class MulticastNewAction(AbstractMulticastData):
    auction_id: int
    processing_server_id: UUID
    title: str
    starting_bid: float
    current_bid: float | None
    auction_owner: str
    current_bidder: str | None
    owner_id: UUID
    client_address: tuple[str, int]
    processing_server_ip: str
    processing_server_port: int


@register_data_type(DataType.MULTICAST_NEW_BID)
@dataclass
class MulticastNewBid(AbstractMulticastData):
    auction_id: int
    new_bid: float
    new_bidder: str | None
