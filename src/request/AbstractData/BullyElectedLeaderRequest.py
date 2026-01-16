from dataclasses import dataclass

from request.AbstractData.AbstractData import AbstractData, register_data_type, DataType

@register_data_type(DataType.BULLY_ELECTED_LEADER_REQUEST)
@dataclass
class BullyElectedLeaderRequest(AbstractData):
    host: str
    uuid: int
    ip: str
    port: int