from dataclasses import dataclass
from typing import Optional

from request.AbstractData.AbstractData import AbstractData, register_data_type, DataType


@register_data_type(DataType.AUCTION)
@dataclass
class RetrieveAuctions(AbstractData):
    uuid: UUID

