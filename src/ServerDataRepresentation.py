from dataclasses import dataclass


@dataclass
class ServerDataRepresentation:
    UUID: str
    ip: str
    port: int