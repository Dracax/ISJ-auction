import uuid
from dataclasses import dataclass

from request.AbstractData.AbstractData import register_data_type, DataType, AbstractData


@register_data_type(DataType.MULTICAST_HEARTBEAT_ACK)
@dataclass
class MulticastHeartbeatAck(AbstractData):
    server: uuid.UUID
    heartbeat_round: int
