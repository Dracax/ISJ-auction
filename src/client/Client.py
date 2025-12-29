import logging
import threading

import logging_config
from AbstractClientOrServer import AbstractClientOrServer
from BroadcastAnnounceRequest import BroadcastAnnounceRequest
from BroadcastAnnounceResponse import BroadcastAnnounceResponse
from Socket import Socket


class Client(AbstractClientOrServer):
    def __init__(self):
        super(Client, self).__init__()

        self.client_socket: Socket | None = None

        self.server_list: list[tuple[str, int]] = []
        self.server_to_talk_to: tuple[str, int] | None = None

    def run(self):
        logging_config.setup_logging(logging.DEBUG)
        logging.info("Starting client process with PID %d", self.pid)
        self.client_socket = Socket()
        self.client_socket.bind((self.ip, 0))

        self.port = self.client_socket.getsockname()[1]
        self.address = (self.ip, self.port)
        logging.info(f"Client bound to {self.ip}:{self.port}")

        thread = threading.Thread(target=self.broadcast_sender, args=(self.get_broadcast_address(), 8000), daemon=True)
        thread.start()
        thread.join()

        self.client_socket.sendto("Hello Server".encode(), self.server_to_talk_to)  # only for testing

        while True:
            data, _ = self.client_socket.receive_data(BroadcastAnnounceResponse)
            logging.debug("Received data: %s", data)

    def broadcast_sender(self, ip, port=37020):
        logging.debug("Starting broadcast sender")

        broadcast_socket = self.create_broadcast_socket()

        message = BroadcastAnnounceRequest(self.host, self.ip, self.port)

        data = broadcast_socket.send_and_receive_data(message, (ip, port), BroadcastAnnounceResponse, timeout=5, retries=10)

        if data:
            logging.info("Received broadcast response: %s", data)
            self.server_list = list(map(tuple, data.server_addresses))
            self.server_to_talk_to = tuple(data.leader_address)

        broadcast_socket.close()


if __name__ == "__main__":
    logging_config.setup_logging(logging.DEBUG)
    client = Client()
    client.start()
    client.join()
