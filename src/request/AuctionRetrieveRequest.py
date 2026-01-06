from dataclasses import dataclass

from request.AbstractRequest import AbstractRequest


@dataclass
class AuctionRetrieveRequest(AbstractRequest):
    only_open: bool
