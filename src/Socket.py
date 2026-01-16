import dataclasses
import enum
import json
import logging
import socket
import typing
import uuid
from typing import get_origin, get_args

from request.AbstractData.AbstractData import AbstractData, DATA_TYPE_REGISTRY, DataType


def _convert_value(value, expected_type):
    if value is None:
        return None

    # handle forward-ref strings
    if isinstance(expected_type, str):
        try:
            expected_type = eval(expected_type, globals(), locals())
        except Exception:
            return value

    origin = get_origin(expected_type)
    args = get_args(expected_type)

    # UUID
    if expected_type is uuid.UUID:
        return uuid.UUID(value)

    # Enum
    if isinstance(expected_type, type) and issubclass(expected_type, enum.Enum):
        return expected_type(value)

    # dataclass (nested)
    if dataclasses.is_dataclass(expected_type) and isinstance(value, dict):
        kwargs = {}
        for f in dataclasses.fields(expected_type):
            if f.name in value:
                kwargs[f.name] = _convert_value(value[f.name], f.type)
        return expected_type(**kwargs)

    # List / Tuple
    if origin in (list, tuple) and args:
        item_type = args[0]
        return type(value)(_convert_value(v, item_type) for v in value)

    # Dict
    if origin is dict and args:
        val_type = args[1]
        return {k: _convert_value(v, val_type) for k, v in value.items()}

    # Optional / Union
    if origin is typing.Union:
        non_none = [a for a in args if a is not type(None)]
        if not non_none:
            return value
        for candidate in non_none:
            try:
                return _convert_value(value, candidate)
            except Exception:
                continue
        return value

    # fallback
    return value


def parse_json_to_dataclass(json_bytes: bytes, data_class: type):
    data_dict = json.loads(json_bytes)
    if not dataclasses.is_dataclass(data_class):
        raise TypeError("data_class must be a dataclass type")
    kwargs = {}
    for f in dataclasses.fields(data_class):
        if f.name in data_dict:
            kwargs[f.name] = _convert_value(data_dict[f.name], f.type)
        elif f.default is not dataclasses.MISSING:
            kwargs[f.name] = f.default
        elif f.default_factory is not dataclasses.MISSING:
            kwargs[f.name] = f.default_factory()
    if "data_type" in kwargs:
        kwargs.pop("data_type")
    return data_class(**kwargs)


class Socket(socket.socket):
    def __init__(self, family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=-1, fileno=None):
        super().__init__(family, type, proto, fileno)

    def send_data(self, data: AbstractData, address: tuple[str, int]):
        if not dataclasses.is_dataclass(data):
            raise TypeError("data must be a dataclass instance")
        logging.debug(f"Sending {data} to {address}")
        self.sendto(str.encode(self.to_json(data)), address)

    def receive_data(self) -> tuple[AbstractData, tuple[str, int]]:
        logging.debug("Trying to receive data")
        data, address = self.recvfrom(1024)
        if not data:
            raise ValueError("No data received")
        logging.debug(f"Received {data} from {address}")
        try:
            response = Socket.parse_to_data(data)
        except json.decoder.JSONDecodeError:
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
    def parse_to_data(raw_data: bytes) -> AbstractData | None:
        if not raw_data:
            return None

        try:
            data_dict = json.loads(raw_data)
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON: {e}")
            return None

        if not data_dict or 'data_type' not in data_dict:
            logging.warning("Missing 'data_type' field in received data")
            return None

        try:
            data_type = DataType(data_dict['data_type'])
        except ValueError as e:
            logging.error(f"Invalid data_type value: {data_dict['data_type']}")
            return None

        if data_type not in DATA_TYPE_REGISTRY:
            logging.error(f"Unknown data type: {data_type}")
            return None

        data_class = DATA_TYPE_REGISTRY[data_type]
        return parse_json_to_dataclass(raw_data, data_class)
