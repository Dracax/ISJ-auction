from dataclasses import dataclass, field

from request.AbstractData.AbstractData import AbstractData


@dataclass
class AbstractRequest(AbstractData):
    request_address: tuple[str, int]
    first_arrival: bool = field(default=False, init=False)  # Indicates if this is the first arrival of the request
