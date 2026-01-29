import asyncio
import logging
import multiprocessing
import os
import socket
import uuid
from asyncio import Event

import logging_config
from AbstractClientOrServer import AbstractClientOrServer
from ServerDataRepresentation import ServerDataRepresentation
from Socket import Socket
from auction.AuctionManager import AuctionManager
from auction.AuctionModel import Auction
from request.AbstractData.AbstractClientRequest import AbstractClientRequest
from request.AbstractData.AuctionBid import AuctionBid
from request.AbstractData.AuctionBidResponse import AuctionPlaceResponse, AuctionBidResponse
from request.AbstractData.BroadcastAnnounceRequest import BroadcastAnnounceRequest
from request.AbstractData.BroadcastAnnounceResponse import BroadcastAnnounceResponse
from request.AbstractData.BullyAcceptVotingParticipationResponse import BullyAcceptVotingParticipationResponse
from request.AbstractData.BullyElectedLeaderRequest import BullyElectedLeaderRequest
from request.AbstractData.FailStopMsg import FailStopMsg
from request.AbstractData.MulticastGroupResponse import MulticastGroupResponse
from request.AbstractData.MulticastNewAction import MulticastNewAction, MulticastNewBid
from request.AbstractData.NotLeaderResponse import NotLeaderResponse
from request.AbstractData.PlaceAuctionData import PlaceAuctionData
from request.AbstractData.RetrieveAuctions import RetrieveAuctions
from request.AbstractData.ServerPlaceAuction import ServerPlaceAuction
from request.AbstractData.SubscribeAuction import SubscribeAuction
from request.AbstractData.SyncDataRequest import SyncDataRequest
from request.AbstractData.UnicastVoteRequest import UnicastVoteRequest
from server.MsgMiddleware import MsgMiddleware


class Server(multiprocessing.Process, AbstractClientOrServer):
    MULTICAST_GROUP = '224.1.1.1'
    MULTICAST_TEST_PORT = 8011
    IS_PRODUCTION = os.environ.get('PRODUCTION', 'true') == 'true'
    UNICAST_PORT = 0 if IS_PRODUCTION else 9001
    TEST_LEADER = os.environ.get('LEADER', 'false') == 'true'

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
        self.ip = self.get_local_ip()
        self.multicast_port: int = None
        self.multicast_address: tuple[str, int] = None

        # middleware
        self.middleware: MsgMiddleware = None

        self.server_id = uuid.uuid4()
        logging.info(self.server_id)
        self.server_list: list[tuple[str, int]] = []
        self.other_server_list: list[ServerDataRepresentation] = []
        self.leader: ServerDataRepresentation = None

        # Bully Algo - use asyncio Events
        self.response_participation_event: Event = None
        self.response_election_event: Event = None

        self.auction_server_map: dict[int, ServerDataRepresentation] = {}

        # dict of auctions
        self.auctions: dict[int, Auction] = {}

    def run(self):
        # Configure logging for this process
        logging_config.setup_logging(logging.DEBUG)
        if self.IS_PRODUCTION:
            logging.info("Production: starting server process with PID %d", os.getpid())
        else:
            logging.info("Development: starting server process with PID %d", os.getpid())

        # Run the async main loop
        asyncio.run(self._async_run())

    async def _async_run(self):
        """Main async entry point for the server."""
        # Initialize asyncio events
        self.response_participation_event = asyncio.Event()
        self.response_election_event = asyncio.Event()

        # unicast socket
        self.unicast_socket: Socket = self.create_unicast_socket()
        self.unicast_socket.bind((self.ip, self.UNICAST_PORT))
        self.port = self.unicast_socket.getsockname()[1]
        self.address = (self.ip, self.port)
        self.other_server_list.append(ServerDataRepresentation(self.server_id, self.ip, self.port))
        logging.info(f"Server bound to {self.ip}:{self.port}")

        # broadcast socket
        ADDRESS = ("", self.SERVER_BROADCAST_PORT)
        self.broadcast_socket: Socket = self.create_broadcast_socket()
        self.broadcast_socket.bind(ADDRESS)

        # Run dynamic discovery in executor (blocking I/O)
        test = asyncio.create_task(
            self.dynamic_discovery_server_broadcast(
                self.get_broadcast_address(),
                self.SERVER_BROADCAST_PORT)
        )

        self.send_socket = Socket()

        self.middleware = MsgMiddleware(self.server_id, {
            self.unicast_socket: 'unicast',
            self.broadcast_socket: 'broadcast',
        })
        if not self.IS_PRODUCTION:
            self.middleware.add_server(uuid.UUID("2add30b2-5762-4046-bf81-0acdd8cbde2c"))  # for testing

        self.auction_manager = AuctionManager()

        # Run middleware and message receiver concurrently
        await asyncio.gather(
            self.middleware.run(),
            self.receive_message()
        )

    async def dynamic_discovery(self, data: BroadcastAnnounceRequest, addr: tuple[str, int]):
        if data.ip == self.ip and data.port == self.port:
            return
        if self.is_leader() and not data.is_server:
            self.send_socket.send_data(BroadcastAnnounceResponse(self.server_list, self.address), data.request_address)
        elif self.multicast_socket and data.is_server:
            logging.info("New server joining: %s", data)
            self.middleware.add_server(data.uuid)
            self.other_server_list.append(ServerDataRepresentation(data.uuid, data.ip, data.port))
            self.send_socket.send_data(MulticastGroupResponse(self.MULTICAST_GROUP, self.multicast_port), data.request_address)
            await self.bully_algo()

    async def dynamic_discovery_server_broadcast(self, ip, port):
        """Blocking method - should be run in executor."""
        logging.debug("Starting broadcast sender")

        broadcast_socket = self.create_broadcast_socket()
        broadcast_socket.bind((self.ip, 0))

        message = BroadcastAnnounceRequest(broadcast_socket.getsockname(), self.host, self.ip, self.port, self.server_id, True)

        data: MulticastGroupResponse | None
        data = broadcast_socket.send_and_receive_data(message, (ip, port), MulticastGroupResponse, timeout=0.2, retries=2)

        if data:
            logging.info("Subscribing to existing multicast group at %s:%d", data.group_address, data.group_port)
            self.multicast_socket = self.setup_multicast_socket(data.group_address, data.group_port)
            self.multicast_port = data.group_port
            self.multicast_address = (data.group_address, data.group_port)
        else:
            logging.info("No broadcast response received, creating new multicast group")
            self.multicast_socket = self.setup_multicast_socket(self.MULTICAST_GROUP,
                                                                self.MULTICAST_TEST_PORT if not self.IS_PRODUCTION else 0)
            self.multicast_port = self.multicast_socket.getsockname()[1]
            self.multicast_address = (self.MULTICAST_GROUP, self.multicast_port)
            logging.info("Created multicast group at %s:%d", self.MULTICAST_GROUP, self.multicast_port)
            self.leader = ServerDataRepresentation(self.server_id, self.ip, self.port)

        broadcast_socket.close()
        await self.middleware.add_socket(self.multicast_socket, 'multicast')

    def is_leader(self) -> bool:
        return self.leader is not None and self.leader.uuid == self.server_id

    async def bully_algo(self):
        """Async bully algorithm implementation."""
        logging.info("** Starting bully algo **")

        logging.info("** Own Server Id: %s **", self.server_id)
        if len(self.other_server_list) <= 0:
            logging.info("** Stopping bully algo due to empty server list **")
            return

        for current_server in self.other_server_list:
            logging.info("** Comparing to Server ID: %s **", current_server.uuid)
            if current_server.uuid.int > self.server_id.int:
                logging.info("** Compared Server ID is bigger, sending vote request: %s **", self.server_id)
                self.send_socket.send_data(UnicastVoteRequest("sadfsad", self.server_id, self.ip, self.port),
                                           (current_server.ip, current_server.port))

        logging.info("** Sent all election messages to servers in list, waiting now for possible responses **")

        # Wait for participation response with timeout
        try:
            await asyncio.wait_for(self.response_participation_event.wait(), timeout=1.0)
            logging.info("** A higher ID server responded to participate in vote event**")

            # Wait for election response with timeout
            try:
                await asyncio.wait_for(self.response_election_event.wait(), timeout=1.0)
                logging.info("** A higher ID server has been elected**")
                self.response_participation_event.clear()
                self.response_election_event.clear()
                return
            except asyncio.TimeoutError:
                pass
        except asyncio.TimeoutError:
            pass

        logging.info("** No response received in timeout, proceeding with winning election. **")
        self.middleware.send_multicast(BullyElectedLeaderRequest("Host idk TODO", self.server_id, self.ip, self.port),
                                       (self.MULTICAST_GROUP, self.multicast_port))
        self.leader = ServerDataRepresentation(self.server_id, self.ip, self.port)

        # Reset events for next time
        self.response_participation_event.clear()
        self.response_election_event.clear()

    async def receive_message(self):
        try:
            logging.info("Server waiting for messages...")
            while True:
                data, addr = await self.middleware.message_queue.get()
                logging.info("Server received message: %s from %s", data, addr)

                if isinstance(data, SubscribeAuction):
                    raise Exception("Not Implemented")

                # If not leader, respond with NotLeaderResponse
                if isinstance(data, AbstractClientRequest) and not self.is_leader() and data.first_arrival:
                    self.send_socket.send_data(NotLeaderResponse(False, (self.leader.ip, self.leader.port)), data.request_address)
                    continue
                elif isinstance(data, AbstractClientRequest):
                    data.first_arrival = False  # mark that the request has arrived once

                match data:
                    case BroadcastAnnounceRequest():
                        asyncio.create_task(self.dynamic_discovery(data, addr))
                    case BullyElectedLeaderRequest():
                        logging.info("** Setting election event participation to true **")
                        self.response_election_event.set()
                        if data.uuid < self.server_id:
                            asyncio.create_task(self.bully_algo())
                        else:
                            logging.info("** Saving new Leader:" + str(data.uuid) + " **")
                            temp = ServerDataRepresentation(data.uuid, data.ip, data.port)
                            self.leader = temp
                    case UnicastVoteRequest():  # Is called by a Server which is performing bully Algo. If their ID is lower, send back a participation message (makes them stop bully for a timeout period)
                        if data.uuid < self.server_id:
                            self.unicast_socket.send_data(BullyAcceptVotingParticipationResponse("idk TODO", self.server_id, self.ip, self.port),
                                                          (data.ip, data.port))
                            asyncio.create_task(self.bully_algo())
                    case BullyAcceptVotingParticipationResponse():
                        logging.info("** Setting ok event participation to true **")
                        self.response_participation_event.set()
                    case RetrieveAuctions():
                        if self.is_leader():
                            self.send_socket.send_data(self.auction_manager.get_all_auctions(), addr)
                    case SubscribeAuction():
                        raise Exception("Not implemented yet")
                    case AuctionBid():
                        await self.handle_bid(data)
                    case PlaceAuctionData():
                        await self.place_auction(data)
                    case ServerPlaceAuction():
                        if data.processing_server_id != self.server_id:
                            logging.error("Wrong server received msg", exc_info=True)
                            continue
                        self.auction_manager.add_auction(data)
                        self.auction_server_map[data.auction_id] = ServerDataRepresentation(self.server_id, self.ip, self.port)
                        if not data.reassignment:
                            self.send_socket.send_data(AuctionPlaceResponse(True, data.auction_id, "sdfgsdfrgdfg"), data.client_address)
                        self.middleware.send_multicast(
                            MulticastNewAction(data.auction_id, data.processing_server_id,
                                               data.title, data.starting_bid, data.current_bid,
                                               data.auction_owner, data.current_bidder, data.owner_id, data.client_address,
                                               processing_server_ip=self.ip, processing_server_port=self.port),
                            (self.MULTICAST_GROUP, self.multicast_port))
                    case MulticastNewAction():
                        self.auction_manager.add_auction(data)
                        self.auction_server_map[data.auction_id] = ServerDataRepresentation(data.processing_server_id,
                                                                                            data.processing_server_ip,
                                                                                            data.processing_server_port)
                    case FailStopMsg():
                        await self.handle_fail_of_server(data)
                    case SyncDataRequest():
                        pass
                    case MulticastNewBid():
                        self.auction_manager.set_bid(data)
                    case _:
                        pass

        except Exception as e:
            logging.error("Error in receive_message: %s", e, exc_info=True)
            self.middleware.send_multicast(FailStopMsg(self.server_id, self.is_leader(), []), self.multicast_address)
            self.kill()

    async def place_auction(self, auction: PlaceAuctionData):
        auction_servers = set(self.auction_server_map.values())
        auction_id = self.auction_manager.get_next_auction_id()
        for server in self.other_server_list:
            if server.uuid != self.server_id and server not in auction_servers:
                self.auction_server_map[auction_id] = server
                break
        else:
            self.auction_server_map[auction_id] = ServerDataRepresentation(self.server_id, self.ip, self.port)

        responsible_server = self.auction_server_map[auction_id]
        self.send_socket.send_data(ServerPlaceAuction(auction_id,
                                                      responsible_server.uuid, auction.title,
                                                      auction.starting_bid, auction.starting_bid, auction.auction_owner, None, auction.owner_id,
                                                      auction.request_address),
                                   (responsible_server.ip, responsible_server.port))

    async def handle_bid(self, bid: AuctionBid):
        if bid.auction_id not in self.auction_server_map:
            if not self.is_leader():
                return
            logging.error("Auction ID not found in auction server map", exc_info=True)
            self.send_socket.send_data(AuctionBidResponse(False, bid.bid_id, "Auction not found."), bid.request_address)
        elif self.is_leader() and self.auction_server_map[bid.auction_id].uuid != self.server_id:
            responsible_server = self.auction_server_map[bid.auction_id]
            logging.info(f"Forwarding bid for auction {bid.auction_id} to server {responsible_server.uuid}")
            self.send_socket.send_data(bid, (responsible_server.ip, responsible_server.port))
        else:
            response = self.auction_manager.handle_bid(bid)
            if response.success:
                self.middleware.send_multicast(MulticastNewBid(bid.auction_id, bid.bid, bid.name), self.multicast_address)
            self.send_socket.send_data(response, bid.request_address)

    async def handle_fail_of_server(self, data: FailStopMsg):
        logging.info("Received fail stop msg from %s", data.stop_id)
        self.other_server_list = [server for server in self.other_server_list if server.uuid != data.stop_id]

        if data.is_leader:
            logging.info("Leader has failed, starting bully algo")
            self.leader = None
            await self.bully_algo()

        auctions_of_failed_server = [auction_id for auction_id, server in self.auction_server_map.items() if server.uuid == data.stop_id]
        self.auction_server_map = {auction_id: server for auction_id, server in self.auction_server_map.items() if server.uuid != data.stop_id}

        if self.is_leader():
            for auction_id in auctions_of_failed_server:
                for server in self.other_server_list:
                    if server.uuid != self.server_id and server.uuid != data.stop_id:
                        self.auction_server_map[auction_id] = server
                        logging.info("Reassigning auction %d to server %s", auction_id, server.uuid)
                        auction = self.auction_manager.auctions[auction_id]
                        self.send_socket.send_data(ServerPlaceAuction(auction_id,
                                                                      server.uuid, auction.item_name,
                                                                      auction.starting_price, auction.current_price, auction.item_owner,
                                                                      auction.current_bidder,
                                                                      None,
                                                                      auction.client_address, True),
                                                   (server.ip, server.port))
                        break
                else:
                    self.auction_server_map[auction_id] = ServerDataRepresentation(self.server_id, self.ip, self.port)
                    logging.info("Reassigning auction %d to self as no other servers available", auction_id)


async def main():
    logging_config.setup_logging(logging.INFO)
    servers = []
    import random
    await asyncio.sleep(random.randint(1, 5) * 0.5)
    try:
        for i in range(1):
            server = Server(instance_index=i)
            server.start()
            await asyncio.sleep(1)
            servers.append(server)

        # Wait for all servers in executor since join() is blocking
        loop = asyncio.get_event_loop()
        for server in servers:
            logging.info("Joining Servers")
            await loop.run_in_executor(None, server.join)

    except KeyboardInterrupt:
        logging.info("Shutting down servers")
        for server in servers:
            server.terminate()
            server.join()


if __name__ == "__main__":
    asyncio.run(main())
