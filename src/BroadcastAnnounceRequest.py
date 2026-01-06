from dataclasses import dataclass

from AbstractData import AbstractData


@dataclass
class BroadcastAnnounceRequest(AbstractData):
    host: str
    ip: str
    port: int
    is_server: bool = False
