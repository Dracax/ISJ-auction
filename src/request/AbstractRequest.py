from dataclasses import dataclass

from AbstractData import AbstractData


@dataclass
class AbstractRequest(AbstractData):
    request_address: tuple[str, int]
