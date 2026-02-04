from dataclasses import dataclass
from uuid import UUID

from request.AbstractData.AbstractData import register_data_type, DataType
from request.AbstractData.AbstractMulticastData import AbstractMulticastData


@register_data_type(DataType.MULTICAST_JOIN_ANNOUNCE)
@dataclass
class MulticastJoinAnnounce(AbstractMulticastData):
    host: str
    ip: str
    port: int
    uuid: UUID
    server_tcp_port: int
