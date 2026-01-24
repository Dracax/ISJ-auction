from dataclasses import dataclass
from uuid import UUID

from request.AbstractData.AbstractData import AbstractData, register_data_type, DataType

@register_data_type(DataType.UNICAST_VOTE_REQUEST)
@dataclass
class UnicastVoteRequest(AbstractData):
    host: str
    uuid: UUID
    ip: str
    port: int