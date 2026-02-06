from dataclasses import dataclass

from request.AbstractData.AbstractData import AbstractData, register_data_type, DataType


@register_data_type(DataType.MULTICAST_GROUP_RESPONSE)
@dataclass
class MulticastGroupResponse(AbstractData):
    group_address: str
    group_port: int
    group_view: list[dict]
    auctions: list[dict]
