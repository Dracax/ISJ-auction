from dataclasses import dataclass

from request.AbstractData.AbstractData import register_data_type, DataType
from request.AbstractData.AbstractMulticastData import AbstractMulticastData


@register_data_type(DataType.SYNCDATA_REQUEST)
@dataclass
class SyncDataRequest(AbstractMulticastData):
    request_address: tuple[str, int]
