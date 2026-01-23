import dataclasses
import json
import logging
import socket
from uuid import UUID

from request.AbstractData.AbstractData import AbstractData, DATA_TYPE_REGISTRY, DataType


class Socket(socket.socket):
    def __init__(self, family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=-1, fileno=None):
        super().__init__(family, type, proto, fileno)

    def send_data(self, data: AbstractData, address: tuple[str, int]):
        if not dataclasses.is_dataclass(data):
            raise TypeError("data must be a dataclass instance")
        logging.debug(f"Sending {data} to {address}")
        self.sendto(str.encode(self.to_json(data)), tuple(address))

    def receive_data(self) -> tuple[AbstractData, tuple[str, int]]:
        data, address = self.recvfrom(1024)
        if not data:
            raise ValueError("No data received")
        logging.debug(f"Received {data} from {address}")
        try:
            response = Socket.parse_to_data(data)
        except json.decoder.JSONDecodeError:
            logging.error(f"Could not parse data: {data}")
            return None, address
        if response is None:
            raise ValueError("Failed to parse data")
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
                data, address, = self.receive_data()
                if data:
                    return data
            except socket.timeout:
                logging.warning("Socket timed out")
                continue

        return None

    def to_json(self, data_class: AbstractData) -> str:
        dataclass = dataclasses.asdict(data_class)  # noqa
        return json.dumps(dataclass, default=lambda o: getattr(o, "value", str(o)))

    @staticmethod
    def parse_to_data(data: bytes) -> AbstractData | None:
        if not data:
            return None

        data_dict = json.loads(data)

        if not data_dict or 'data_type' not in data_dict:
            return None

        data_type = DataType(data_dict['data_type'])

        if data_type not in DATA_TYPE_REGISTRY:
            raise ValueError(f"Unknown data type: {data_type}")

        data_class = DATA_TYPE_REGISTRY[data_type]
        data_dict.pop('data_type')

        # Separate init=True and init=False fields
        init_fields = {}
        post_init_fields = {}

        for f in dataclasses.fields(data_class):
            if f.name in data_dict:
                value = data_dict[f.name]
                # Convert UUID strings back to UUID objects
                if f.type == UUID and isinstance(value, str):
                    value = UUID(value)
                if f.init:
                    init_fields[f.name] = value
                else:
                    post_init_fields[f.name] = value

        # Create instance with init fields only
        instance = data_class(**init_fields)

        # Set the init=False fields after creation
        for name, value in post_init_fields.items():
            setattr(instance, name, value)

        return instance
