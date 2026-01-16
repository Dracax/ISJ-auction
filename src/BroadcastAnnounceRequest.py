from dataclasses import dataclass

from AbstractData import AbstractData, register_data_type, DataType


@register_data_type(DataType.BROADCAST_ANNOUNCE_REQUEST)
@dataclass
class BroadcastAnnounceRequest(AbstractData):
    host: str
    ip: str
    port: int
    uuid: str
    is_server: bool = False
