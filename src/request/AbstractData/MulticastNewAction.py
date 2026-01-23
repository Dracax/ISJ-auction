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
    auction_owner: str
    owner_id: UUID
    processing_server_ip: str
    processing_server_port: int
