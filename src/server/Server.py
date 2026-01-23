import logging
import multiprocessing
import os
import socket
import threading
import time
import uuid
import json

import logging_config
from AbstractClientOrServer import AbstractClientOrServer
from ServerDataRepresentation import ServerDataRepresentation
from Socket import Socket
from request.AbstractData.BroadcastAnnounceRequest import BroadcastAnnounceRequest
from request.AbstractData.BroadcastAnnounceResponse import BroadcastAnnounceResponse
from request.AbstractData.MulticastGroupResponse import MulticastGroupResponse
from request.AbstractData.UnicastVoteRequest import UnicastVoteRequest
from server.MsgMiddleware import MsgMiddleware
from auction.AuctionModel import Auction
from auction.AuctionManager import AuctionManager


class Server(multiprocessing.Process, AbstractClientOrServer):
    MULTICAST_GROUP = '224.0.0.1'
    MULTICAST_TEST_PORT = 8011
    IS_PRODUCTION = os.environ.get('PRODUCTION', 'true') == 'true'

    SERVER_BROADCAST_PORT = 8000

    def __init__(self, instance_index: int):
        super(Server, self).__init__()

        self.instance_index = instance_index

        # Sockets
        self.unicast_socket: Socket = None
        self.broadcast_socket: Socket = None
        # will be set after dynamic discovery
        self.multicast_socket: Socket | None = None

        self.send_socket: Socket = None

        self.host = socket.gethostname()
        self.ip = socket.gethostbyname(self.host)
        self.multicast_port: int = None

        # middleware
        self.middleware: MsgMiddleware = None

        self.server_id = uuid.uuid4()
        logging.debug(self.server_id)
        self.server_list: list[tuple[str, int]] = []
        self.other_server_list: list[ServerDataRepresentation] = []

        # dict of auctions
        self.auctions: dict[int, Auction] = {}

    def run(self):
        # Configure logging for this process
        logging_config.setup_logging(logging.DEBUG)
        if self.IS_PRODUCTION:
            logging.info("Production: starting server process with PID %d", os.getpid())
        else:
            logging.info("Development: starting server process with PID %d", os.getpid())

        # unicast socket
        self.unicast_socket: Socket = self.create_unicast_socket()
        self.unicast_socket.bind((self.ip, 0))
        self.port = self.unicast_socket.getsockname()[1]
        self.address = (self.ip, self.port)
        self.other_server_list.append(ServerDataRepresentation(self.server_id, self.ip, self.port))
        logging.info(f"Server bound to {self.ip}:{self.port}")

        # broadcast socket
        ADDRESS = ("0.0.0.0", 8000)
        self.broadcast_socket: Socket = self.create_broadcast_socket()
        self.broadcast_socket.bind(ADDRESS)

        threading.Thread(target=self.dynamic_discovery_server_broadcast,
                         args=(self.get_broadcast_address(), self.SERVER_BROADCAST_PORT), daemon=True).start()

        self.send_socket = Socket()

        self.middleware = MsgMiddleware(self.server_id, {
            self.unicast_socket: 'unicast',
            self.broadcast_socket: 'broadcast',
        })
        if not self.IS_PRODUCTION:
            self.middleware.add_server(uuid.UUID("2add30b2-5762-4046-bf81-0acdd8cbde2c"))  # for testing

        self.middleware.start()

        self.auction_manager = AuctionManager(
            middleware=self.middleware,
            broadcast_addr=(self.MULTICAST_GROUP, self.multicast_port)
        )


        self.receive_message()
        self.middleware.join()



    def dynamic_discovery(self, data: BroadcastAnnounceRequest, addr: tuple[str, int]):
        if data.ip == self.ip and data.port == self.port:
            return
        if self.is_leader() and not data.is_server:
            self.unicast_socket.send_data(BroadcastAnnounceResponse(self.server_list, self.address), addr)
        elif self.multicast_socket and data.is_server:
            logging.info("New server joining: %s", data)
            self.middleware.add_server(data.uuid)
            self.other_server_list.append(ServerDataRepresentation(data.uuid, data.ip, data.port))
            self.unicast_socket.send_data(MulticastGroupResponse(self.MULTICAST_GROUP, self.multicast_port), addr)

    def dynamic_discovery_server_broadcast(self, ip, port=37020):
        logging.debug("Starting broadcast sender")

        broadcast_socket = self.create_broadcast_socket()
        message = BroadcastAnnounceRequest(self.host, self.ip, self.port, self.server_id, True)

        data: MulticastGroupResponse | None  # to satisfy type checker
        data = broadcast_socket.send_and_receive_data(message, (ip, port), MulticastGroupResponse, timeout=1,
                                                      retries=2)

        if data:
            logging.info("Subscribing to existing multicast group at %s:%d", data.group_address, data.group_port)
            self.multicast_socket = self.setup_multicast_socket(data.group_address, data.group_port)
            self.multicast_port = data.group_port
        else:
            logging.info("No broadcast response received, creating new multicast group")
            self.multicast_socket = self.setup_multicast_socket(self.MULTICAST_GROUP, self.MULTICAST_TEST_PORT if not self.IS_PRODUCTION else 0)
            self.multicast_port = self.multicast_socket.getsockname()[1]
            logging.info("Created multicast group at %s:%d", self.MULTICAST_GROUP, self.multicast_port)

        broadcast_socket.close()
        self.middleware.add_socket(self.multicast_socket, 'multicast')

    def is_leader(self) -> bool:
        return self.instance_index == 0  # TODO: implement leader election

    def bully_algo(self):
        # Bully Algo send vote request to all server with bigger UUID than self
        logging.info("Starting bully algo")
        logging.info("Own Server Id: %s", self.server_id)
        for current_server in self.other_server_list:
            if current_server.uuid.int > self.server_id.int:  # todo: DOES THIS WORK?
                logging.info("Compared Server ID is bigger, sending vote request: %s", self.server_id)
                # Unicast msg to server
                data: UnicastVoteRequest | None  # to satisfy type checker
                self.unicast_socket.send_data(UnicastVoteRequest("sadfsad", self.ip, self.port), (current_server.ip, current_server.port))
        # Now wait if anyone with higher id responds

        # No Replies from others, sending won election to all servers in multicast group
        # TODO: Multicast msg to all servers
        return

    def receive_message(self):
        while True:
            data, addr = self.middleware.message_queue.get()
            logging.info("Server received message: %s from %s", data, addr)
            # TODO call method acording to msg
            match data:
                case BroadcastAnnounceRequest():
                    self.dynamic_discovery(data, addr)


if __name__ == "__main__":
    logging_config.setup_logging(logging.DEBUG)
    servers = []
    try:
        for i in range(1):
            server = Server(instance_index=i)
            server.start()
            time.sleep(4)
            servers.append(server)
        for server in servers:
            server.join()
    except KeyboardInterrupt:
        logging.info("Shutting down servers")
        for server in servers:
            server.terminate()
            server.join()
