from dataclasses import dataclass
from uuid import UUID

from request.AbstractData.AbstractData import AbstractData, register_data_type, DataType

@register_data_type(DataType.BULLY_ACCEPT_VOTING_PARTICIPATION_RESPONSE)
@dataclass
class BullyAcceptVotingParticipationResponse(AbstractData):
    host: str
    uuid: UUID
    ip: str
    port: int