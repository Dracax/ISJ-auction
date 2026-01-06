import dataclasses
import json
import logging
import socket

from AbstractData import AbstractData


class Socket(socket.socket):
    def __init__(self, family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=-1, fileno=None):
        super().__init__(family, type, proto, fileno)

    def send_data(self, data: AbstractData, address: tuple[str, int]):
        if not dataclasses.is_dataclass(data):
            raise TypeError("data must be a dataclass instance")
        logging.debug(f"Sending {data} to {address}")
        self.sendto(str.encode(json.dumps(dataclasses.asdict(data))), address)  # noqa

    def receive_data[T: AbstractData](self, response_type: type[T]) -> tuple[T, tuple[str, int]]:
        logging.debug(f"Trying to receive data of type {response_type}")
        data, address = self.recvfrom(1024)
        if not data:
            raise ValueError("No data received")
        data_dict = json.loads(data)
        response = response_type(**data_dict)
        logging.debug(f"Received {response} from {address}")
        return response, address

    def send_and_receive_data[T: AbstractData](
            self,
            data: AbstractData,
            address: tuple[str, int],
            response_type: type[T],
            timeout: float | None = None,
            retries: int = 0
    ) -> T | None:
        if timeout is not None:
            self.settimeout(timeout)

        for _ in range(retries + 1):
            self.send_data(data, address)
            try:
                data, address, = self.receive_data(response_type)
                if data:
                    return data
            except socket.timeout:
                logging.warning("Socket timed out")
                continue

        return None
