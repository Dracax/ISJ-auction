import logging
import multiprocessing
import socket
import threading

import logging_config
from AbstractClientOrServer import AbstractClientOrServer
from BroadcastAnnounceRequest import BroadcastAnnounceRequest
from BroadcastAnnounceResponse import BroadcastAnnounceResponse
from Socket import Socket
from server.MulticastGroupResponse import MulticastGroupResponse


class Server(multiprocessing.Process, AbstractClientOrServer):
    MULTICAST_GROUP = '224.0.0.1'
    SERVER_BROADCAST_PORT = 8002

    def __init__(self, instance_index: int):
        super(Server, self).__init__()

        self.instance_index = instance_index
        self.server_socket: Socket | None = None

        self.host = socket.gethostname()
        self.ip = socket.gethostbyname(self.host)
        self.multicast_port: int = None

        self.multicast_socket = None

        self.server_list: list[tuple[str, int]] = []

    def run(self):
        # Configure logging for this process
        logging_config.setup_logging(logging.DEBUG)
        logging.info("Starting server instance")
        self.server_socket: Socket | None = Socket()

        self.server_socket.bind((self.ip, 0))
        self.port = self.server_socket.getsockname()[1]
        self.address = (self.ip, self.port)
        self.server_list.append(self.address)

        logging.info(f"Server bound to {self.ip}:{self.port}")

        # client broadcast listener
        threading.Thread(target=self.broadcast_listen, daemon=True).start()
        # server broadcast listener
        threading.Thread(target=self.broadcast_listen, args=(self.SERVER_BROADCAST_PORT,), daemon=True).start()
        # server broadcast sender
        threading.Thread(target=self.broadcast_sender, args=(self.get_broadcast_address(), self.SERVER_BROADCAST_PORT), daemon=True).start()

        while True:
            data, address = self.server_socket.recvfrom(1024)
            logging.debug("Received data: %s", data)

    def broadcast_listen(self, port=8000):
        logging.debug("Starting broadcast listener")
        listen_socket = Socket()
        ADDRESS = ("0.0.0.0", port)

        listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        listen_socket.bind(ADDRESS)
        logging.info("Broadcast listener bound to %s:%d", ADDRESS[0], ADDRESS[1])

        while True:
            data: BroadcastAnnounceRequest  # to satisfy type checker
            data, addr = listen_socket.receive_data(BroadcastAnnounceRequest)
            if data:
                if data.ip == self.ip and data.port == self.port:
                    continue
                logging.debug("Received data: %s from %s", data, addr)
                if self.is_leader() and not data.is_server:
                    listen_socket.send_data(BroadcastAnnounceResponse(self.server_list, self.address), addr)
                elif self.multicast_socket and self.is_leader() and data.is_server:
                    logging.info("New server joining: %s", data)
                    self.server_list.append((data.ip, data.port))
                    listen_socket.send_data(MulticastGroupResponse(self.MULTICAST_GROUP, self.multicast_port), addr)

    def broadcast_sender(self, ip, port=37020):
        logging.debug("Starting broadcast sender")

        broadcast_socket = self.create_broadcast_socket()
        message = BroadcastAnnounceRequest(self.host, self.ip, self.port, True)

        data: MulticastGroupResponse | None  # to satisfy type checker
        data = broadcast_socket.send_and_receive_data(message, (ip, port), MulticastGroupResponse, timeout=1, retries=2)

        if data:
            logging.info("Subscribing to existing multicast group at %s:%d", data.group_address, data.group_port)
            self.multicast_socket = self.setup_multicast_socket(data.group_address, data.group_port)
            self.multicast_port = data.group_port
        else:
            logging.info("No broadcast response received, creating new multicast group")
            self.multicast_socket = self.setup_multicast_socket(self.MULTICAST_GROUP, 0)
            self.multicast_port = self.multicast_socket.getsockname()[1]
            logging.info("Created multicast group at %s:%d", self.MULTICAST_GROUP, self.multicast_port)

        broadcast_socket.close()

    def is_leader(self) -> bool:
        return self.instance_index == 0  # TODO: implement leader election


if __name__ == "__main__":
    logging_config.setup_logging(logging.DEBUG)
    servers = []
    try:
        for i in range(1):
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
