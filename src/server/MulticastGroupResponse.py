from dataclasses import dataclass

from AbstractData import AbstractData, register_data_type, DataType


@register_data_type(DataType.MULTICAST_GROUP_RESPONSE)
@dataclass
class MulticastGroupResponse(AbstractData):
    group_address: str
    group_port: int
