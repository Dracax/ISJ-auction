from dataclasses import dataclass
from uuid import UUID

from request.AbstractData.AbstractData import DataType, register_data_type
from request.AbstractData.AbstractMulticastData import AbstractMulticastData


@register_data_type(DataType.MULTICAST_MSG_REQUEST)
@dataclass
class MulticastMsgRequest(AbstractMulticastData):
    requested_ids: list[int]
    requested_server_id: UUID
