from dataclasses import dataclass
from uuid import UUID


@dataclass
class ServerDataRepresentation:
    uuid: UUID
    ip: str
    port: int
