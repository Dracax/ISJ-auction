from dataclasses import dataclass

from request.AbstractData.AbstractData import AbstractData


@dataclass
class AbstractRequest(AbstractData):
    request_address: tuple[str, int]
