from dataclasses import dataclass
from uuid import UUID

from request.AbstractData.AbstractData import register_data_type, DataType
from request.AbstractRequest import AbstractRequest


@register_data_type(DataType.BROADCAST_ANNOUNCE_REQUEST)
@dataclass
class BroadcastAnnounceRequest(AbstractRequest):
    host: str
    ip: str
    port: int
    uuid: UUID
    is_server: bool = False
    server_tcp_port: int | None = None
