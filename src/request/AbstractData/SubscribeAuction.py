from dataclasses import dataclass
from uuid import UUID

from request.AbstractData.AbstractData import AbstractData, register_data_type, DataType


@register_data_type(DataType.AUCTION_SUBSCRIBE)
@dataclass
class SubscribeAuction(AbstractData):
    uuid: UUID
    auction_id: int
