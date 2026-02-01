from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ServerDataRepresentation:
    uuid: UUID
    ip: str
    port: int
    tpc_port: int
