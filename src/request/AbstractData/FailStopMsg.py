from dataclasses import dataclass
from uuid import UUID

from request.AbstractData.AbstractData import register_data_type, DataType
from request.AbstractData.AbstractMulticastData import AbstractMulticastData


@register_data_type(DataType.FAIL_STOP_MSG)
@dataclass
class FailStopMsg(AbstractMulticastData):
    stop_id: UUID
    is_leader: bool
    open_transactions: list[int]
