from dataclasses import dataclass
from uuid import UUID

from request.AbstractData.AbstractData import register_data_type, DataType, AbstractData


@register_data_type(DataType.SERVER_ACUTION_PLACE)
@dataclass
class ServerPlaceAuction(AbstractData):
    auction_id: int
    processing_server_id: UUID
    title: str
    starting_bid: float
    current_bid: float | None
    auction_owner: str
    current_bidder: str
    owner_id: UUID
    client_address: tuple[str, int]
    reassignment: bool = False
    response_address: tuple[str, int] | None = None
