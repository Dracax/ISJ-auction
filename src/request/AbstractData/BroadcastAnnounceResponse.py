from dataclasses import dataclass

from request.AbstractData.AbstractData import AbstractData, register_data_type, DataType


@register_data_type(DataType.BROADCAST_ANNOUNCE_RESPONSE)
@dataclass
class BroadcastAnnounceResponse(AbstractData):
    server_addresses: list[tuple[str, int]]
    leader_address: tuple[str, int]
