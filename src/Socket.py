import dataclasses
import json
import socket

from AbstractData import AbstractData


class Socket(socket.socket):
    def __init__(
        self, family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=-1, fileno=None
    ):
        super().__init__(family, type, proto, fileno)

    def send_data(self, data: AbstractData, address: tuple[str, int]):
        if not dataclasses.is_dataclass(data):
            raise TypeError("data must be a dataclass instance")
        self.sendto(str.encode(json.dumps(dataclasses.asdict(data))), address)  # noqa

    def receive_data[T: AbstractData](
        self, response_type: type[T]
    ) -> tuple[T, tuple[str, int]]:
        data, address = self.recvfrom(1024)
        if not data:
            raise ValueError("No data received")
        data_dict = json.loads(data)
        response = response_type(**data_dict)
        return response, address