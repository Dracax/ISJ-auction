from dataclasses import dataclass

from AbstractData import AbstractData


@dataclass
class AbstractRequest(AbstractData):
    request_type: str  # e.g., "AUCTION_RETRIEVE", "BID_PLACEMENT"
    request_address: tuple[str, int]
