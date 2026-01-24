from dataclasses import dataclass
from uuid import UUID

from request.AbstractData.AbstractData import register_data_type, DataType
from request.AbstractRequest import AbstractRequest


@register_data_type(DataType.AUCTION_SUBSCRIBE)
@dataclass
class SubscribeAuction(AbstractRequest):
    uuid: UUID
    auction_id: int
