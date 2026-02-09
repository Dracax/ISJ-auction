from dataclasses import dataclass
from uuid import UUID

from request.AbstractData.AbstractData import register_data_type, DataType
from request.AbstractData.AbstractMulticastData import AbstractMulticastData


@register_data_type(DataType.BULLY_ELECTED_LEADER_REQUEST)
@dataclass
class BullyElectedLeaderRequest(AbstractMulticastData):
    uuid: UUID
    ip: str
    port: int
    tpc_port: int
