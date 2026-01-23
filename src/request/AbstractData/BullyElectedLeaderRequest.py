from dataclasses import dataclass
from uuid import UUID

from request.AbstractData.AbstractData import AbstractData, register_data_type, DataType

@register_data_type(DataType.BULLY_ELECTED_LEADER_REQUEST)
@dataclass
class BullyElectedLeaderRequest(AbstractData):
    host: str
    uuid: UUID
    ip: str
    port: int