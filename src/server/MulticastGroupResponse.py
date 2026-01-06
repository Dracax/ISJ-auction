from dataclasses import dataclass

from AbstractData import AbstractData


@dataclass
class MulticastGroupResponse(AbstractData):
    group_address: str
    group_port: int
