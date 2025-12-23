import logging
import multiprocessing
import socket
import threading

import logging_config
from BroadcastAnnounceRequest import BroadcastAnnounceRequest
from BroadcastAnnounceResponse import BroadcastAnnounceResponse
from Socket import Socket


class Client(multiprocessing.Process):
    def __init__(self):
        super(Client, self).__init__()

        self.client_socket: Socket | None = None
        self.client_address: tuple[str, int] | None = None

        self.server_list: list[tuple[str, int]] = []
        self.server_to_talk_to: tuple[str, int] | None = None

    def run(self):
        logging_config.setup_logging(logging.DEBUG)
        logging.info("Starting client process with PID %d", self.pid)
        self.client_socket = Socket()
        self.client_address = socket.gethostname()
        self.client_socket.bind((self.client_address, 0))

        threading.Thread(
            target=self.broadcast_sender, args=("255.255.255.255", 8000), daemon=True
        ).start()

        while True:
            data, address = self.client_socket.receive_data(BroadcastAnnounceResponse)
            logging.debug("Received data: %s", data)

    def broadcast_sender(self, ip, port=37020):
        logging.debug("Starting broadcast sender")

        broadcast_socket = Socket()
        # Enable permission to send to broadcast addresses
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        my_host = socket.gethostname()
        my_ip = socket.gethostbyname(my_host)

        message = BroadcastAnnounceRequest(my_host, my_ip, 80)

        broadcast_socket.send_data(message, (ip, port))

        data, server = broadcast_socket.receive_data(BroadcastAnnounceResponse)
        if data:
            logging.info("Received broadcast response: %s", data)
            self.server_list = data.server_list
            self.server_to_talk_to = data.leader_address

        broadcast_socket.close()


if __name__ == "__main__":
    logging_config.setup_logging(logging.DEBUG)
    client = Client()
    client.start()
    client.join()