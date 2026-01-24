from dataclasses import dataclass, field
from enum import Enum


class DataType(Enum):
    BROADCAST_ANNOUNCE_REQUEST = "BroadcastAnnounceRequest"
    BROADCAST_ANNOUNCE_RESPONSE = "BroadcastAnnounceResponse"
    MULTICAST_GROUP_RESPONSE = "MulticastGroupResponse"
    AUCTION_RETRIEVE_REQUEST = "AuctionRetrieveRequest"
    UNICAST_VOTE_REQUEST = "UnicastVoteRequest"
    BULLY_ELECTED_LEADER_REQUEST = "BullyElectedLeaderRequest"
    BULLY_ACCEPT_VOTING_PARTICIPATION_RESPONSE = "BullyAcceptVotingParticipationResponse"
    MULTICAST_MSG_REQUEST = "MulticastMsgRequest"
    TEST = "TestMulticast"
    AUCTION_BID = "AuctionBid"
    AUCTION_BID_RESPONSE = "AuctionBidResponse"
    AUCTION_RETRIEVE = "RetrieveAuctions"
    AUCTION_RETRIEVE_RESPONSE = "RetrieveAuctionsResponse"
    AUCTION_SUBSCRIBE = "SubscribeAuction"
    ACUTION_PLACE = "PlaceAuction"
    SERVER_ACUTION_PLACE = "ServerPlaceAuction"
    MULTICAST_NEW_AUCTION = "MulticastNewAuction"
    AUCTION_PLACE_RESPONSE = "PlaceAuctionResponse"
    NOT_LEADER_RESPONSE = "NotLeaderResponse"


@dataclass
class AbstractData:
    data_type: DataType = field(init=False)


DATA_TYPE_REGISTRY: dict[DataType, type[AbstractData]] = {}


def register_data_type(type_name: DataType):
    def decorator(cls: type[AbstractData]) -> type[AbstractData]:
        DATA_TYPE_REGISTRY[type_name] = cls
        cls.data_type = type_name
        return cls

    return decorator
