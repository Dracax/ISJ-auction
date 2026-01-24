from dataclasses import dataclass
from uuid import UUID

from request.AbstractData.AbstractClientRequest import AbstractClientRequest
from request.AbstractData.AbstractData import register_data_type, DataType


@register_data_type(DataType.AUCTION_SUBSCRIBE)
@dataclass
class SubscribeAuction(AbstractClientRequest):
    uuid: UUID
    auction_id: int
