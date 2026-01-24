from dataclasses import dataclass, field

from request.AbstractRequest import AbstractRequest


@dataclass
class AbstractClientRequest(AbstractRequest):
    first_arrival: bool = field(default=True, init=False)  # Indicates if this is the first arrival of the request
