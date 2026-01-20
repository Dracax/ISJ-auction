from dataclasses import dataclass, field
from uuid import UUID

from request.AbstractData.AbstractData import AbstractData


@dataclass
class AbstractMulticastData(AbstractData):
    sender_uuid: UUID = field(init=False)
    sequence_number: int = field(init=False)
    msg_type: str = field(init=False, default=None)
