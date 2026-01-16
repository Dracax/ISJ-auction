import logging
import multiprocessing
import socket
import threading
import uuid

import logging_config
from AbstractClientOrServer import AbstractClientOrServer
from AbstractData import AbstractData
from BroadcastAnnounceRequest import BroadcastAnnounceRequest
from BroadcastAnnounceResponse import BroadcastAnnounceResponse
from ServerDataRepresentation import ServerDataRepresentation
from Socket import Socket
from UnicastVoteRequest import UnicastVoteRequest
from server.MsgMiddleware import MsgMiddleware
from server.MulticastGroupResponse import MulticastGroupResponse


class Server(multiprocessing.Process, AbstractClientOrServer):
    MULTICAST_GROUP = '224.0.0.1'
    SERVER_BROADCAST_PORT = 8002

    def __init__(self, instance_index: int):
        super(Server, self).__init__()

        self.instance_index = instance_index

        # Sockets
        self.unicast_socket: Socket = None
        self.broadcast_socket: Socket = None
        # will be set after dynamic discovery
        self.multicast_socket: Socket | None = None

        self.host = socket.gethostname()
        self.ip = socket.gethostbyname(self.host)
        self.multicast_port: int = None

        # middleware
        self.middleware: MsgMiddleware = None

        self.server_id = uuid.uuid4()
        logging.debug(self.server_id)
        self.server_list: list[tuple[str, int]] = []
        self.other_server_list: list[ServerDataRepresentation] = []

    def run(self):
        # Configure logging for this process
        logging_config.setup_logging(logging.DEBUG)
        logging.info("Starting server instance")

        # unicast socket
        self.unicast_socket: Socket = self.create_unicast_socket()
        self.unicast_socket.bind((self.ip, 0))
        self.port = self.unicast_socket.getsockname()[1]
        self.address = (self.ip, self.port)
        self.other_server_list.append(ServerDataRepresentation(self.server_id, self.ip, self.port))
        logging.info(f"Server bound to {self.ip}:{self.port}")

        # broadcast socket
        ADDRESS = ("0.0.0.0", 8000)
        self.broadcast_socket: Socket = Socket()
        self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # <-- Hinzufügen

        self.broadcast_socket.bind(ADDRESS)

        self.middleware = MsgMiddleware(self)
        threading.Thread(target=self.broadcast_listen, daemon=True).start()
        self.middleware.start()
        self.middleware.join()

        # # client broadcast listener
        # # server broadcast listener
        # threading.Thread(target=self.broadcast_listen, args=(self.SERVER_BROADCAST_PORT,), daemon=True).start()
        # # server broadcast sender
        # threading.Thread(target=self.dynamic_discovery_server_broadcast,
        #                  args=(self.get_broadcast_address(), self.SERVER_BROADCAST_PORT), daemon=True).start()
        #
        # while True:
        #     data, address = self.unicast_socket.recvfrom(1024)
        #     logging.debug("Received data: %s", data)

    def broadcast_listen(self, port=8000):
        logging.debug("Starting broadcast listener")
        listen_socket = Socket()
        ADDRESS = ("0.0.0.0", port)

        listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        listen_socket.bind(ADDRESS)
        logging.info("Broadcast listener bound to %s:%d", ADDRESS[0], ADDRESS[1])

        while True:
            data: BroadcastAnnounceRequest  # to satisfy type checker
            data, addr = listen_socket.receive_data()
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

    def dynamic_discovery_server_broadcast(self, ip, port=37020):
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

    def bully_algo(self):
        # Bully Algo send vote request to all server with bigger UUID than self
        logging.info("Starting bully algo")
        logging.info("Own Server Id: %s", self.server_id)
        for current_server in self.other_server_list:
            if current_server.UUID > str(self.server_id):  # todo: DOES THIS WORK?
                logging.info("Compared Server ID is bigger, sending vote request: %s", self.server_id)
                # Unicast msg to server
                data: UnicastVoteRequest | None  # to satisfy type checker
                current_server_socket = self.create_unicast_socket()
                current_server_socket.send_data(UnicastVoteRequest(), current_server.address)
        # Now wait if anyone with higher id responds

        # No Replies from others, sending won election to all servers in multicast group
        # TODO: Multicast msg to all servers
        return

    def receive_message(self, msg: AbstractData):
        # TODO call method acording to msg
        # midleware --> receive_message

        match msg:  # TODO: isinstance?
            case UnicastVoteRequest:
                pass


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
