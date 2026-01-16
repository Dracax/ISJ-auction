from dataclasses import dataclass

from request.AbstractData.AbstractData import AbstractData, register_data_type, DataType

@register_data_type(DataType.BULLY_ACCEPT_VOTING_PARTICIPATION_RESPONSE)
@dataclass
class BullyAcceptVotingParticipationResponse(AbstractData):
    host: str
    uuid: str
    ip: str
    port: int