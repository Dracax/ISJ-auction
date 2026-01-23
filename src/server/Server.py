import logging
import multiprocessing
import os
import socket
import threading
import time
import uuid
import asyncio

import logging_config
from AbstractClientOrServer import AbstractClientOrServer
from ServerDataRepresentation import ServerDataRepresentation
from Socket import Socket
from auction.AuctionManager import AuctionManager
from auction.AuctionModel import Auction
from request.AbstractData.AuctionBid import AuctionBid
from request.AbstractData.BroadcastAnnounceRequest import BroadcastAnnounceRequest
from request.AbstractData.BroadcastAnnounceResponse import BroadcastAnnounceResponse
from ServerDataRepresentation import ServerDataRepresentation
from Socket import Socket
from request.AbstractData.BullyAcceptVotingParticipationResponse import BullyAcceptVotingParticipationResponse
from request.AbstractData.BullyElectedLeaderRequest import BullyElectedLeaderRequest
from request.AbstractData.MulticastGroupResponse import MulticastGroupResponse
from request.AbstractData.PlaceAuctionData import PlaceAuctionData
from request.AbstractData.RetrieveAuctions import RetrieveAuctions
from request.AbstractData.SubscribeAuction import SubscribeAuction
from request.AbstractData.UnicastVoteRequest import UnicastVoteRequest
from server.MsgMiddleware import MsgMiddleware
from multiprocessing import Event


class Server(multiprocessing.Process, AbstractClientOrServer):
    MULTICAST_GROUP = '224.1.1.1'
    MULTICAST_TEST_PORT = 8011
    IS_PRODUCTION = os.environ.get('PRODUCTION', 'true') == 'true'
    UNICAST_PORT = 0 if IS_PRODUCTION else 9001

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
        self.leader: ServerDataRepresentation = None

        # Bully Algo
        self.electing_new_leader: bool = False
        self.response_participation_event = Event()
        self.response_election_event = Event()

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
        self.unicast_socket.bind((self.ip, self.UNICAST_PORT))
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

        self.auction_manager = AuctionManager()

        self.receive_message()
        self.middleware.join()

    def dynamic_discovery(self, data: BroadcastAnnounceRequest, addr: tuple[str, int]):
        if data.ip == self.ip and data.port == self.port:
            return
        if self.is_leader() and not data.is_server:
            self.send_socket.send_data(BroadcastAnnounceResponse(self.server_list, self.address), (data.ip, data.port))
        elif self.multicast_socket and data.is_server:
            logging.info("New server joining: %s", data)
            self.middleware.add_server(data.uuid)
            self.other_server_list.append(ServerDataRepresentation(data.uuid, data.ip, data.port))
            self.send_socket.send_data(MulticastGroupResponse(self.MULTICAST_GROUP, self.multicast_port), (data.ip, data.port))
            self.bully_algo()

    def dynamic_discovery_server_broadcast(self, ip, port=37020):
        logging.debug("Starting broadcast sender")

        broadcast_socket = self.create_broadcast_socket()
        broadcast_socket.bind((self.ip, 0))

        message = BroadcastAnnounceRequest(self.host, broadcast_socket.getsockname()[0], broadcast_socket.getsockname()[1], self.server_id, True)

        data: MulticastGroupResponse | None  # to satisfy type checker
        data = broadcast_socket.send_and_receive_data(message, (ip, port), MulticastGroupResponse, timeout=1,
                                                      retries=2)

        if data:
            logging.info("Subscribing to existing multicast group at %s:%d", data.group_address, data.group_port)
            self.multicast_socket = self.setup_multicast_socket(data.group_address, data.group_port)
            self.multicast_port = data.group_port
        else:
            logging.info("No broadcast response received, creating new multicast group")
            self.multicast_socket = self.setup_multicast_socket(self.MULTICAST_GROUP,
                                                                self.MULTICAST_TEST_PORT if not self.IS_PRODUCTION else 0)
            self.multicast_port = self.multicast_socket.getsockname()[1]
            logging.info("Created multicast group at %s:%d", self.MULTICAST_GROUP, self.multicast_port)

        broadcast_socket.close()
        self.middleware.add_socket(self.multicast_socket, 'multicast')

    def is_leader(self) -> bool:
        return self.instance_index == 0  # TODO: implement leader election

    def bully_algo(self):
        # Bully Algo send vote request to all server with bigger UUID than self
        logging.info("** Starting bully algo **")

        logging.info("** Own Server Id: %s **", self.server_id)
        self.electing_new_leader = True
        if len(self.other_server_list) <= 0:
            logging.info("** Stopping bully algo due to empty server list **")
            return
        for current_server in self.other_server_list:
            logging.info("** Comparing to Server ID: %s **", current_server.uuid)
            if current_server.uuid.int > self.server_id.int:
                logging.info("** Compared Server ID is bigger, sending vote request: %s **", self.server_id)
                # Unicast msg to server
                data: UnicastVoteRequest | None  # to satisfy type checker
                self.unicast_socket.send_data(UnicastVoteRequest("sadfsad", self.ip, self.port),
                                              (current_server.ip, current_server.port)) # TODO
        # Now wait if anyone with higher id responds
        logging.info("** Sent all election messages to servers in list, waiting now for possible responses **")
        response_received = self.response_participation_event.wait(timeout=2.0)

        if response_received:
            logging.info("** A higher ID server responded to participate in vote event**")
            election_received = self.response_election_event.wait(timeout=2.0)
            if election_received:
                logging.info("** A higher ID server has been elected**")
                self.response_participation_event.clear()
                self.response_election_event.clear()
                return
        logging.info("** No response received in 2 second, proceeding with winning election. **")
        # No Replies from others, sending won election to all servers in multicast group
        self.middleware.send_multicast(BullyElectedLeaderRequest("Host idk TODO", self.server_id, self.ip, self.port), (self.MULTICAST_GROUP, self.multicast_port))

        # Reset event for next time
        self.response_participation_event.clear()
        self.response_election_event.clear()
        return

    def receive_message(self):
        while True:
            data, addr = self.middleware.message_queue.get()
            logging.info("Server received message: %s from %s", data, addr)
            match data:
                case BroadcastAnnounceRequest():
                    #self.dynamic_discovery(data, addr)
                    #logging.debug("** Starting thread for messages **")
                    threading.Thread(target=self.dynamic_discovery, args= (data, addr), daemon=True).start()
                case BullyElectedLeaderRequest():
                    logging.info("** Setting election event participation to true **")
                    self.response_election_event.set()
                    if data.uuid < self.server_id:
                        self.bully_algo()
                    else:
                        logging.info("** Saving new Leader:" + data.uuid + " **")
                        self.electing_new_leader = False
                        temp = ServerDataRepresentation(data.uuid, data.ip, data.port)
                        self.leader = temp
                case UnicastVoteRequest(): # Is called by a Server which is performing bully Algo. If their ID is lower, send back a participation message (makes them stop bully for a timeout period)
                    if data.uuid < self.server_id:
                        self.unicast_socket.send_data(BullyAcceptVotingParticipationResponse("idk TODO", self.server_id, self.ip, self.port), (data.ip, data.port))
                        self.bully_algo()
                case BullyAcceptVotingParticipationResponse(): # Receive when this server is performing bully and someone with higher ID wants to participate.
                    self.electing_new_leader = False
                    logging.info("** Setting ok event participation to true **")
                    self.response_participation_event.set()
                case RetrieveAuctions():
                    self.send_socket.send_data(self.auction_manager.get_all_auctions(), addr)
                case SubscribeAuction():
                    pass
                case AuctionBid():
                    self.send_socket.send_data(self.auction_manager.handle_bid(data), addr)
                case PlaceAuctionData():
                    self.auction_manager.add_auction(data)
                case _:
                    pass

async def main():
    logging_config.setup_logging(logging.DEBUG)
    servers = []
    try:
        for i in range(2):
            server = Server(instance_index=i)
            server.start()
            #time.sleep(4)
            await asyncio.sleep(4)
            servers.append(server)
        #for server in servers:
            #logging.info("Joining Servers")
            #server.join()
        #time.sleep(4)
        await asyncio.sleep(2)
    except KeyboardInterrupt:
        logging.info("Shutting down servers")
        for server in servers:
            server.terminate()
            server.join()

if __name__ == "__main__":
    asyncio.run(main())
