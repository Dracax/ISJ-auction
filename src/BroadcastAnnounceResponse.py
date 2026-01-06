from dataclasses import dataclass

from AbstractData import AbstractData


@dataclass
class BroadcastAnnounceResponse(AbstractData):
    server_addresses: list[tuple[str, int]]
    leader_address: tuple[str, int]
