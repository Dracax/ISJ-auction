from dataclasses import dataclass

from request.AbstractData.AbstractData import AbstractData


@dataclass
class AbstractResponse(AbstractData):
    success: bool
