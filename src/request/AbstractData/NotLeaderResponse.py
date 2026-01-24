from dataclasses import dataclass

from request.AbstractData.AbstractData import register_data_type, DataType
from request.AbstractData.AbstractResponse import AbstractResponse


@register_data_type(DataType.NOT_LEADER_RESPONSE)
@dataclass
class NotLeaderResponse(AbstractResponse):
    leader_address: tuple[str, int]
