import asyncio
import copy
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
from request.AbstractData.AbstractClientRequest import AbstractClientRequest
from request.AbstractData.AuctionBid import AuctionBid
from request.AbstractData.AuctionBidInformation import AuctionBidInformation
from request.AbstractData.AuctionBidResponse import AuctionPlaceResponse, AuctionBidResponse
from request.AbstractData.BroadcastAnnounceRequest import BroadcastAnnounceRequest
from request.AbstractData.BroadcastAnnounceResponse import BroadcastAnnounceResponse
from request.AbstractData.BullyAcceptVotingParticipationResponse import BullyAcceptVotingParticipationResponse
from request.AbstractData.BullyElectedLeaderRequest import BullyElectedLeaderRequest
from request.AbstractData.FailStopMsg import FailStopMsg
from request.AbstractData.MulticastGroupResponse import MulticastGroupResponse
from request.AbstractData.MulticastHeartbeat import MulticastHeartbeat
from request.AbstractData.MulticastHeartbeatAck import MulticastHeartbeatAck
from request.AbstractData.MulticastJoinAnnounce import MulticastJoinAnnounce
from request.AbstractData.MulticastNewAction import MulticastNewAction, MulticastNewBid
from request.AbstractData.NotLeaderResponse import NotLeaderResponse
from request.AbstractData.PlaceAuctionData import PlaceAuctionData
from request.AbstractData.RetrieveAuctions import RetrieveAuctions
from request.AbstractData.ServerPlaceAuction import ServerPlaceAuction
from request.AbstractData.SubscribeAuction import SubscribeAuction
from request.AbstractData.SyncDataRequest import SyncDataRequest
from request.AbstractData.UnicastVoteRequest import UnicastVoteRequest
from server.HeartbeatSenderModule import HeartbeatSenderModule
from server.MsgMiddleware import MsgMiddleware


class Server(multiprocessing.Process, AbstractClientOrServer):
    MULTICAST_GROUP = '224.1.1.1'
    MULTICAST_TEST_PORT = 8011
    IS_PRODUCTION = os.environ.get('PRODUCTION', 'true') == 'true'
    UNICAST_PORT = 0 if IS_PRODUCTION else 9001
    TEST_LEADER = os.environ.get('LEADER', 'false') == 'true'

    SERVER_BROADCAST_PORT = 8000

    def __init__(self):
        super(Server, self).__init__()

        self._bully_task: asyncio.Task | None = None

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

        self.tpc_server = None
        self.tcp_port: int = None

        # middleware
        self.middleware: MsgMiddleware = None
        if not self.IS_PRODUCTION:
            self.server_id = uuid.UUID("ffffffff-5762-4046-bf81-0acdd8cbde2c")  # for testing
        else:
            self.server_id = uuid.uuid4()
        logging.info(self.server_id)
        self.server_group_view: list[ServerDataRepresentation] = []
        self.leader: ServerDataRepresentation = None

        # Bully Algo - use asyncio Events
        self.response_participation_event: Event = None
        self.response_election_event: Event = None

        self.auction_server_map: dict[int, ServerDataRepresentation] = {}
        self.server_id_map: dict[uuid.UUID, ServerDataRepresentation] = {}

        # Heartbeat
        self.heartbeat_sender_task = None
        self.heartbeat_sender: HeartbeatSenderModule = None
        self.heartbeat_listener_task = None
        self._heartbeat_event = None

        self.test = None

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
        self._heartbeat_event = asyncio.Event()
        self._middleware_started_event = asyncio.Event()

        # unicast socket
        self.unicast_socket: Socket = self.create_unicast_socket()
        self.unicast_socket.bind((self.ip, self.UNICAST_PORT))
        self.port = self.unicast_socket.getsockname()[1]
        self.address = (self.ip, self.port)
        logging.info(f"Server bound to {self.ip}:{self.port}")

        # broadcast socket
        ADDRESS = ("", self.SERVER_BROADCAST_PORT)
        self.broadcast_socket: Socket = self.create_broadcast_socket()
        self.broadcast_socket.bind(ADDRESS)

        self.auction_manager = AuctionManager()
        self.dynamic_discovery_server_broadcast(
            self.get_broadcast_address(),
            self.SERVER_BROADCAST_PORT)

        self.middleware = MsgMiddleware(self.server_id, {
            self.unicast_socket: 'unicast',
            self.broadcast_socket: 'broadcast',
            self.multicast_socket: 'multicast'
        },
                                        self.multicast_socket,
                                        self._middleware_started_event)
        self.tpc_server = await asyncio.start_server(self.middleware.handle_client, self.ip, 0)
        self.tcp_port = self.tpc_server.sockets[0].getsockname()[1]

        self.server_id_map[self.server_id] = ServerDataRepresentation(self.server_id, self.ip, self.port, self.tcp_port)
        self.server_group_view.append(self.server_id_map[self.server_id])

        logging.info(f"Initial group view: {self.server_group_view}")
        logging.info(f"TCP server bound to {self.ip}:{self.tcp_port}")
        self.middleware.start_tcp_server(self.tpc_server)

        self.send_socket = Socket()

        if not self.IS_PRODUCTION:
            self.middleware.add_server(uuid.UUID("2add30b2-5762-4046-bf81-0acdd8cbde2c"))  # for testing

        asyncio.create_task(self.announce_server_start())
        # Run middleware and message receiver concurrently
        await asyncio.gather(
            self.middleware.run(),
            self.receive_message()

        )

    async def announce_server_start(self):
        await asyncio.sleep(0.5)
        if not self._middleware_started_event.is_set():
            logging.info("Waiting for middleware to start before announcing server")
            await self._middleware_started_event.wait()
        self.middleware.send_multicast(MulticastJoinAnnounce(self.host, self.ip, self.port, self.server_id, self.tcp_port), self.multicast_address)

    async def dynamic_discovery(self, data: BroadcastAnnounceRequest, addr: tuple[str, int]):
        if data.ip == self.ip and data.port == self.port:
            return
        if self.is_leader() and not data.is_server:
            self.send_socket.send_data(BroadcastAnnounceResponse([(x.ip, x.port) for x in self.server_group_view], self.address),
                                       data.request_address)
        elif self.multicast_socket and data.is_server:
            logging.info("New server joining: %s", data)
            self.middleware.add_server(data.uuid)

            self.send_socket.send_data(MulticastGroupResponse(self.MULTICAST_GROUP, self.multicast_port, self.server_group_view,
                                                              [{"auction_id": x.auction_id,
                                                                "processing_server_id": self.auction_server_map[x.auction_id].uuid,
                                                                "responsible_server_ip": self.auction_server_map[x.auction_id].ip,
                                                                "responsible_server_port": self.auction_server_map[x.auction_id].port,
                                                                "responsible_server_tcp_port":
                                                                    self.auction_server_map[x.auction_id].tpc_port,
                                                                "title": x.item_name,
                                                                "starting_bid": x.starting_price,
                                                                "current_bid": x.current_price,
                                                                "auction_owner": x.item_owner,
                                                                "current_bidder": x.current_bidder,
                                                                "owner_id": x.item_owner,
                                                                "client_address": x.client_address,
                                                                "reassignment": False,
                                                                "current_bidder_address": x.current_bidder_address} for x in
                                                               self.auction_manager.get_all_auctions().auctions]),
                                       data.request_address)

    def dynamic_discovery_server_broadcast(self, ip, port):
        """Blocking method - should be run in executor."""
        logging.debug("Starting broadcast sender")

        broadcast_socket = self.create_broadcast_socket()
        broadcast_socket.bind((self.ip, 0))

        message = BroadcastAnnounceRequest(broadcast_socket.getsockname(), self.host, self.ip, self.port, self.server_id, True, self.tcp_port)

        data: MulticastGroupResponse | None
        data = broadcast_socket.send_and_receive_data(message, (ip, port), MulticastGroupResponse, timeout=1, retries=2)

        if data:
            logging.info("Subscribing to existing multicast group at %s:%d", data.group_address, data.group_port)
            self.multicast_socket = self.setup_multicast_socket(data.group_address, data.group_port)
            self.multicast_port = data.group_port
            self.multicast_address = (data.group_address, data.group_port)
            self.server_group_view.extend([ServerDataRepresentation.of(x) for x in data.group_view])
            self.server_id_map.update({x.uuid: x for x in self.server_group_view})
            for auction in data.auctions:
                server_ip = auction.pop("responsible_server_ip")
                server_port = auction.pop("responsible_server_port")
                server_tcp_port = auction.pop("responsible_server_tcp_port")
                place_auction = ServerPlaceAuction(**auction)
                self.auction_manager.add_auction(place_auction)
                self.auction_server_map[place_auction.auction_id] = ServerDataRepresentation(place_auction.processing_server_id, server_ip,
                                                                                             server_port, server_tcp_port)
        else:
            logging.info("No broadcast response received, creating new multicast group")
            self.multicast_socket = self.setup_multicast_socket(self.MULTICAST_GROUP,
                                                                self.MULTICAST_TEST_PORT if not self.IS_PRODUCTION else 0)
            self.multicast_port = self.multicast_socket.getsockname()[1]
            self.multicast_address = (self.MULTICAST_GROUP, self.multicast_port)
            logging.info("Created multicast group at %s:%d", self.MULTICAST_GROUP, self.multicast_port)
            self.leader = ServerDataRepresentation(self.server_id, self.ip, self.port, self.tcp_port)

        broadcast_socket.close()

    def is_leader(self) -> bool:
        return self.leader is not None and self.leader.uuid == self.server_id

    async def bully_algo(self):
        """Async bully algorithm implementation."""
        logging.info("** Starting bully algo **")

        self.response_participation_event.clear()
        self.response_election_event.clear()

        logging.info("** Own Server Id: %s **", self.server_id)
        if len(self.server_group_view) <= 0 or (len(self.server_group_view) <= 1 and self.server_group_view[0].uuid == self.server_id):
            logging.info("** Stopping bully algo due to empty server list **")
            await self.announce_leadership()
            return
        send_msg = False
        for current_server in self.server_group_view:
            logging.info("** Comparing to Server ID: %s **", current_server.uuid)
            if current_server.uuid.int > self.server_id.int:
                logging.info("** Compared Server ID is bigger, sending vote request: %s **", current_server.uuid)
                self.send_socket.send_data(UnicastVoteRequest("sadfsad", self.server_id, self.ip, self.port),
                                           (current_server.ip, current_server.port))
                send_msg = True

        logging.info("** Sent all election messages to servers in list, waiting now for possible responses **")
        if not send_msg:
            logging.info("** No higher ID servers found, proceeding with winning election. **")
            self.response_participation_event.clear()
            self.response_election_event.clear()
            await self.announce_leadership()
            return

        # Wait for participation response with timeout
        try:
            if self.response_participation_event.is_set():
                logging.info("** Event already set, skipping wait **")
            else:
                await asyncio.wait_for(self.response_participation_event.wait(), timeout=2.0)
            logging.info("** A higher ID server responded to participate in vote event**")
            self.response_participation_event.clear()

            # Wait for election response with timeout
            try:
                if self.response_election_event.is_set():
                    logging.info("** Event already set, skipping wait **")
                else:
                    await asyncio.wait_for(self.response_election_event.wait(), timeout=2.0)
                logging.info("** A higher ID server has been elected**")
                self.response_election_event.clear()
                return
            except asyncio.TimeoutError:
                logging.info("** No election response received in timeout, proceeding with winning election. **")
                pass
        except asyncio.TimeoutError:
            logging.info("** No participation response received in timeout, proceeding with winning election. **")
            pass

        logging.info("** No response received in timeout, proceeding with winning election. **")

        await self.announce_leadership()

    async def announce_leadership(self):
        self.middleware.send_multicast(BullyElectedLeaderRequest("Host idk TODO", self.server_id, self.ip, self.port, self.tcp_port),
                                       (self.MULTICAST_GROUP, self.multicast_port))
        self.leader = self.server_id_map[self.server_id]

        # Reset events for next time
        self.response_participation_event.clear()
        self.response_election_event.clear()

        logging.info(f"** New Leader Elected: {self.leader.uuid} **")

        # Start Heartbeat sender
        await self.restart_heartbeat()

    async def restart_heartbeat(self):
        # Stop Heartbeat Sender task if one is running
        if self.heartbeat_sender_task is not None:
            self.heartbeat_sender_task.cancel()

        if self.heartbeat_listener_task is not None:
            self.heartbeat_listener_task.cancel()

        # Start Heartbeat Sender if this server is the elected leader
        if self.is_leader():
            logging.info("Leader starting heartbeat sender %s", self.server_id)
            self.heartbeat_sender = HeartbeatSenderModule(self)
            self.heartbeat_sender_task = asyncio.create_task(self.heartbeat_sender.run())

        else:
            # Start listening for Heartbeat
            self.heartbeat_listener_task = asyncio.create_task(
                self.wait_for_heartbeat())

    async def wait_for_heartbeat(self):
        logging.info("Starting heartbeat listener")
        while True:
            try:
                if not self._heartbeat_event.is_set():
                    await asyncio.wait_for(
                        self._heartbeat_event.wait(),
                        timeout=HeartbeatSenderModule.LEADER_TIMEOUT  # TODO: No hardcode
                    )

                # Heartbeat received
                logging.debug("heartbeat event received, resetting timeout and sending ACK")
                self._heartbeat_event.clear()
                # Send Unicast ACK to Leaders Heartbeat sender
                self.unicast_socket.send_data(MulticastHeartbeatAck(self.server_id, 0), (self.leader.ip, self.leader.port))

            except asyncio.TimeoutError:
                logging.warning("heartbeat event timed out")

                # TODO: I do not receive the multicast myself, put the same logic here (remove leader from group view, start bully algo, ...)
                # No heartbeat within timeout
                await self.on_heartbeat_timeout(self.leader.uuid, True)
                break
            except Exception as e:
                logging.error("Error in heartbeat listener: %s", e, exc_info=True)
                break

    async def on_heartbeat_timeout(self, crashed_server_id: uuid.UUID, is_leader: bool):
        msg = FailStopMsg(crashed_server_id, is_leader, [])
        # TODO: Handle Open Transactions of leader
        self.middleware.send_multicast(msg, self.multicast_address)

        await self.handle_fail_of_server(msg)

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
                            if self._bully_task is not None:
                                self.cancel_bully_task()
                            self._bully_task = asyncio.create_task(self.bully_algo())
                        else:
                            logging.info("** Saving new Leader:" + str(data.uuid) + " **")
                            if data.uuid in self.server_id_map:
                                self.leader = self.server_id_map[data.uuid]
                            else:
                                self.leader = ServerDataRepresentation(data.uuid, data.ip, data.port, data.tpc_port)
                            # Start Heartbeat listener
                            await self.restart_heartbeat()
                    case MulticastHeartbeat():
                        logging.info("Received Heartbeat - Setting event")
                        self._heartbeat_event.set()
                    case MulticastHeartbeatAck():
                        self.heartbeat_sender.handle_ack(data)
                    case UnicastVoteRequest():  # Is called by a Server which is performing bully Algo. If their ID is lower, send back a participation message (makes them stop bully for a timeout period)
                        if data.uuid < self.server_id:
                            self.unicast_socket.send_data(BullyAcceptVotingParticipationResponse("idk TODO", self.server_id, self.ip, self.port),
                                                          (data.ip, data.port))
                            if self._bully_task is not None:
                                self.cancel_bully_task()
                            self._bully_task = asyncio.create_task(self.bully_algo())
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
                        self.place_server_auction(data)
                    case MulticastNewAction():
                        self.auction_manager.add_auction(data)
                        self.auction_server_map[data.auction_id] = self.server_id_map[data.processing_server_id]
                    case FailStopMsg():
                        await self.handle_fail_of_server(data)
                    case SyncDataRequest():
                        pass
                    case MulticastNewBid():
                        self.auction_manager.set_bid(data)
                    case MulticastJoinAnnounce():
                        self.server_id_map[data.uuid] = ServerDataRepresentation(data.uuid, data.ip, data.port, data.server_tcp_port)
                        if self.server_id_map[data.uuid] in self.server_group_view:
                            logging.warning("Server already in group view: %s", data.uuid)
                        else:
                            self.server_group_view.append(self.server_id_map[data.uuid])
                        if self._bully_task is not None:
                            self.cancel_bully_task()
                        self._bully_task = asyncio.create_task(self.bully_algo())
                    case _:
                        pass

        except Exception as e:
            logging.error("Error in receive_message: %s", e, exc_info=True)
            self.middleware.send_multicast(FailStopMsg(self.server_id, self.is_leader(), []), self.multicast_address)
            await self.stop()

    async def place_auction(self, auction: PlaceAuctionData):
        auction_servers = set(self.auction_server_map.values())
        auction_id = self.auction_manager.get_next_auction_id()
        for server in self.server_group_view:
            if server.uuid != self.server_id and server not in auction_servers:
                response = await self.middleware.send_tcp_message(
                    ServerPlaceAuction(auction_id,
                                       server.uuid, auction.title,
                                       auction.starting_bid, auction.starting_bid,
                                       auction.auction_owner, None,
                                       auction.owner_id,
                                       auction.notification_address,
                                       response_address=auction.request_address),
                    server.tcp_address)
                if response:
                    self.auction_server_map[auction_id] = copy.copy(server)
                    break
        else:
            self.auction_server_map[auction_id] = self.server_id_map[self.server_id]
            self.place_server_auction(ServerPlaceAuction(auction_id,
                                                         self.server_id, auction.title,
                                                         auction.starting_bid, auction.starting_bid,
                                                         auction.auction_owner, None,
                                                         auction.owner_id,
                                                         auction.notification_address,
                                                         response_address=auction.request_address))

    def place_server_auction(self, data: ServerPlaceAuction):
        if data.processing_server_id != self.server_id:
            logging.error("Wrong server received msg", exc_info=True)
            return
        self.auction_manager.add_auction(data)
        self.auction_server_map[data.auction_id] = self.server_id_map[self.server_id]
        if not data.reassignment:
            self.send_socket.send_data(AuctionPlaceResponse(True, data.auction_id, "Auction was placed"), data.response_address)
        self.middleware.send_multicast(
            MulticastNewAction(data.auction_id, data.processing_server_id,
                               data.title, data.starting_bid, data.current_bid,
                               data.auction_owner, data.current_bidder, data.owner_id, data.client_address,
                               processing_server_ip=self.ip, processing_server_port=self.port, current_bidder_address=data.current_bidder_address),
            (self.MULTICAST_GROUP, self.multicast_port))

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
            old_highest_bidder = None
            if bid.auction_id in self.auction_manager.auctions:
                old_highest_bidder = self.auction_manager.auctions[bid.auction_id].current_bidder_address
            response = self.auction_manager.handle_bid(bid)
            if response.success:
                self.middleware.send_multicast(MulticastNewBid(bid.auction_id, bid.bid, bid.name, bid.notification_address), self.multicast_address)
                self.send_socket.send_data(
                    AuctionBidInformation(bid.auction_id, self.auction_manager.auctions[bid.auction_id].item_name, bid.name, bid.bid),
                    self.auction_manager.auctions[bid.auction_id].client_address)
                if old_highest_bidder:
                    self.send_socket.send_data(
                        AuctionBidInformation(bid.auction_id, self.auction_manager.auctions[bid.auction_id].item_name, bid.name, bid.bid,
                                              outbid=True),
                        old_highest_bidder)

            self.send_socket.send_data(response, bid.request_address)

    async def handle_fail_of_server(self, data: FailStopMsg):
        logging.info("Received fail stop msg from %s", data.stop_id)

        # If the apparently failed server is myself TODO: Instead of kms, try to re-join the group
        if data.stop_id == self.server_id:
            await self.stop()

        self.server_group_view = [server for server in self.server_group_view if server.uuid != data.stop_id]

        if data.is_leader:
            logging.info("Leader has failed, starting bully algo")
            self.leader = None
            await self.bully_algo()  # TODO

        auctions_of_failed_server = [auction_id for auction_id, server in self.auction_server_map.items() if server.uuid == data.stop_id]
        self.auction_server_map = {auction_id: server for auction_id, server in self.auction_server_map.items() if server.uuid != data.stop_id}

        if self.is_leader():
            logging.info("Reassigning auctions of failed server %s", data.stop_id)
            for auction_id in auctions_of_failed_server:
                for server in self.server_group_view:
                    logging.info("Checking server %s for reassignment of auction %d", server.uuid, auction_id)
                    if server.uuid != self.server_id and server.uuid != data.stop_id:
                        self.auction_server_map[auction_id] = server
                        logging.info("Reassigning auction %d to server %s", auction_id, server.uuid)
                        auction = self.auction_manager.auctions[auction_id]
                        self.send_socket.send_data(ServerPlaceAuction(auction_id,
                                                                      server.uuid, auction.item_name,
                                                                      auction.starting_price, auction.current_price, auction.item_owner,
                                                                      auction.current_bidder,
                                                                      None,
                                                                      auction.client_address, True,
                                                                      current_bidder_address=auction.current_bidder_address),
                                                   (server.ip, server.port))
                        break
                else:
                    self.auction_server_map[auction_id] = self.server_id_map[self.server_id]
                    logging.info("Reassigning auction %d to self as no other servers available", auction_id)

    def cancel_bully_task(self):
        return
        if self._bully_task is not None:
            self._bully_task.cancel()
            self._bully_task = None

        self.response_participation_event.clear()
        self.response_participation_event.clear()

    async def stop(self):
        # Cancel all tasks in the current event loop
        await asyncio.sleep(0.1)  # Give some time for the message to be sent before shutting down
        self.middleware.stop()
        loop = asyncio.get_running_loop()
        tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
        for task in tasks:
            task.cancel()

        os._exit(1)


async def main():
    logging_config.setup_logging(logging.INFO)
    servers = []
    import random
    await asyncio.sleep(random.randint(1, 5) * 0.5)
    try:
        for i in range(1):
            server = Server()
            server.start()
            await asyncio.sleep(2)
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
