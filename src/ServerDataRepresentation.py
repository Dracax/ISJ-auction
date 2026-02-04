from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ServerDataRepresentation:
    uuid: UUID
    ip: str
    port: int
    tpc_port: int

    @staticmethod
    def of(data: dict) -> "ServerDataRepresentation":
        return ServerDataRepresentation(
            uuid=UUID(data["uuid"]),
            ip=data["ip"],
            port=data["port"],
            tpc_port=data["tpc_port"]
        )

    @property
    def tcp_address(self) -> tuple[str, int]:
        return self.ip, self.tpc_port

    @property
    def udp_address(self) -> tuple[str, int]:
        return self.ip, self.port
