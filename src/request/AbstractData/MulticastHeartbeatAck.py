from dataclasses import dataclass

from request.AbstractData.AbstractData import register_data_type, DataType
from request.AbstractData.AbstractMulticastData import AbstractMulticastData

@register_data_type(DataType.MULTICAST_HEARTBEAT_ACK)
@dataclass
class MulticastHeartbeatAck(AbstractMulticastData):
    heartbeat_round: int
    ip: str
    port: int