import logging
import socket
import threading
import uuid

import logging_config
from AbstractClientOrServer import AbstractClientOrServer
from Socket import Socket
from request.AbstractData.AbstractData import AbstractData
from request.AbstractData.BroadcastAnnounceRequest import BroadcastAnnounceRequest
from request.AbstractData.BroadcastAnnounceResponse import BroadcastAnnounceResponse
from request.AbstractRequest import AbstractRequest


class Client(threading.Thread, AbstractClientOrServer):
    def __init__(self):
        super(Client, self).__init__()

        self.client_socket: Socket | None = None

        self.host = socket.gethostname()
        self.ip = socket.gethostbyname(self.host)

        self.server_list: list[tuple[str, int]] = []
        self.server_to_talk_to: tuple[str, int] | None = None

    def run(self):
        logging_config.setup_logging(logging.DEBUG)
        # logging.info("Starting client process with PID %d", self.pid)
        self.client_socket = Socket()
        self.client_socket.bind((self.ip, 0))

        self.client_socket.settimeout(5)  # For testing very high timeout

        self.port = self.client_socket.getsockname()[1]
        self.address = (self.ip, self.port)
        logging.info(f"Client bound to {self.ip}:{self.port}")

        thread = threading.Thread(target=self._start_dynamic_discovery, args=(self.get_broadcast_address(), 8000),
                                  daemon=True)
        thread.start()
        thread.join()

        self.client_socket.sendto("Hello Server".encode(), self.server_to_talk_to)  # only for testing

    def _start_dynamic_discovery(self, ip, port=37020):
        logging.debug("Starting broadcast sender")

        broadcast_socket = self.create_broadcast_socket()

        message = BroadcastAnnounceRequest(self.host, self.ip, self.port,
                                           uuid.uuid4())  # TODO: generate uuid do we need it?

        data = broadcast_socket.send_and_receive_data(message, (ip, port), BroadcastAnnounceResponse, timeout=5, retries=10)

        if data:
            logging.info("Received broadcast response: %s", data)
            self.server_list = list(map(tuple, data.server_addresses))
            self.server_to_talk_to = tuple(data.leader_address)

        broadcast_socket.close()

    def send_get_request[T: AbstractData](self, request: AbstractRequest, response_type: type[T]) -> T | None:
        if not self.client_socket or not self.server_to_talk_to:
            logging.error("Client socket or server address not set")
            return None

        request.request_address = self.client_socket.getsockname()

        response = self.send_and_receive_data(request, response_type)

        if response:
            logging.info("Received response: %s", response)
        else:
            logging.warning("No response received for request: %s", request)

        return response

    def send_and_receive_data[T: AbstractData](
            self,
            data: AbstractRequest,
            response_type: type[T],
            retries: int = 0
    ) -> T | None:

        is_success = False
        data_received = None
        for server in [self.server_to_talk_to] + self.server_list:
            self.client_socket.send_data(data, server)
            try:
                data_received, _, = self.client_socket.receive_data()
                if data_received:
                    is_success = True
                    break
            except socket.timeout:
                logging.warning("Socket timed out, trying new ip/port")

        if data_received:
            return data_received

        if not is_success or data_received is None:
            self._start_dynamic_discovery(self.get_broadcast_address(), 8000)

        try:
            self.client_socket.send_data(data, self.server_to_talk_to)
            data_received, address, = self.client_socket.receive_data()
        except socket.timeout:
            logging.warning("Socket timed out on retry after rediscovery")
            logging.info("Try again later..")
            return None
        if data_received:
            return data_received

        return None


if __name__ == "__main__":
    logging_config.setup_logging(logging.DEBUG)
    client = Client()
    client.start()
    client.join()
