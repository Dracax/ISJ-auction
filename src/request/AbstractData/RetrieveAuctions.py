from dataclasses import dataclass
from uuid import UUID

from request.AbstractData.AbstractData import AbstractData, register_data_type, DataType


@register_data_type(DataType.AUCTION_RETRIEVE)
@dataclass
class RetrieveAuctions(AbstractData):
    uuid: UUID
