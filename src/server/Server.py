import dataclasses
import json
import logging
import multiprocessing
import socket
import threading

from plotly.validators.layout.geo import ScopeValidator

import logging_config
from BroadcastAnnounceRequest import BroadcastAnnounceRequest
from BroadcastAnnounceResponse import BroadcastAnnounceResponse
from Socket import Socket


class Server(multiprocessing.Process):
    def __init__(self, instance_index: int):
        super(Server, self).__init__()

        self.instance_index = instance_index
        self.server_socket: Socket | None = None

        self.server_address = ("127.0.0.1", 10001 + self.instance_index)

        self.server_list: list[tuple[str, int]] = []
        self.server_list.append(self.server_address)

    def run(self):
        # Configure logging for this process
        logging_config.setup_logging(logging.DEBUG)
        logging.info("Starting server instance %d", self.instance_index)
        self.server_socket: Socket | None = Socket()

        self.server_socket.bind(self.server_address)

        threading.Thread(target=self.broadcast_listen, daemon=True).start()

        while True:
            data, address = self.server_socket.recvfrom(1024)
            logging.debug("Received data: %s", data)

    def broadcast_listen(self):
        logging.debug("Starting broadcast listener")
        listen_socket = Socket()
        BROADCAST_PORT = 8000
        ADDRESS = ("0.0.0.0", BROADCAST_PORT)

        listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        listen_socket.bind(ADDRESS)
        logging.info("Broadcast listener bound to %s:%d", ADDRESS[0], ADDRESS[1])

        while True:
            data, addr = listen_socket.receive_data(BroadcastAnnounceRequest)
            if data:
                logging.debug("Received data: %s from %s", data, addr)
                if self.is_leader() and not data.is_server:
                    listen_socket.send_data(BroadcastAnnounceResponse(self.server_list, self.server_address), addr)


    def is_leader(self) -> bool:
        return self.instance_index == 0  # TODO: implement leader election


if __name__ == "__main__":
    logging_config.setup_logging(logging.DEBUG)
    servers = []
    try:
        for i in range(2):
            server = Server(instance_index=i)
            server.start()
            servers.append(server)
        for server in servers:
            server.join()
    except KeyboardInterrupt:
        logging.info("Shutting down servers")
        for server in servers:
            server.terminate()
            server.join()
