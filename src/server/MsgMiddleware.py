import asyncio
import json
import logging
from uuid import UUID

from Socket import Socket
from request.AbstractData.AbstractData import AbstractData
from request.AbstractData.AbstractMulticastData import AbstractMulticastData
from request.AbstractData.MulticastMsgRequest import MulticastMsgRequest
from server.UniquePriorityQueue import UniquePriorityQueue, PrioritizedItem


class MsgMiddleware:
    def __init__(self, server_id: UUID, sockets: dict[Socket, str], multicast_socket: Socket, start_event: asyncio.Event):
        super(MsgMiddleware, self).__init__()
        self.server_id = server_id
        self.sockets = sockets
        self._running = False
        self.multicast_socket = multicast_socket
        self.start_event = start_event

        self.tcp_server_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

        self._handlers = {
            'broadcast': self._handle_broadcast_message,
            'unicast': self._handle_unicast_message,
            'multicast': self._handle_multicast_message
        }

        # Queue for thread communication
        self.message_queue: asyncio.Queue[tuple[AbstractData, tuple[str, int]]] = asyncio.Queue()
        self.outgoing_multicast_queue: asyncio.Queue[tuple[AbstractMulticastData, tuple[str, int]]] = asyncio.Queue()
        self._socket_tasks: dict[Socket, asyncio.Task] = {}

        # testing
        self.msg_ids = [2, 1, 4, 3, 0]

        # multicast variables
        self.current_sequence_number = 0
        self.server_sequence_numbers: dict[UUID, int] = {}

        self.sender_cache: dict[int, AbstractMulticastData] = {}
        self.server_queues: dict[UUID, UniquePriorityQueue] = {}

    async def run(self):
        # event loop
        logging.info("Starting MsgMiddleware")
        self._running = True

        try:
            async with self._lock:
                for sock, msg_type in self.sockets.items():
                    self._start_socket_task(sock, msg_type)

            outgoing_task = asyncio.create_task(self._process_outgoing_messages())
            self.start_event.set()
            while self._running:
                await asyncio.sleep(1.0)
            outgoing_task.cancel()
        except Exception as e:
            logging.error("MsgMiddleware run error: %s", e)
            await self.stop()

    def _start_socket_task(self, sock: Socket, message_type: str):
        """Create a dedicated receive task for a socket."""
        task = asyncio.create_task(self._socket_receive_loop(sock, message_type))
        self._socket_tasks[sock] = task
        logging.info("Started receive task for socket type: %s", message_type)

    def start_tcp_server(self, server):
        self.tcp_server_task = asyncio.create_task(self._start_tcp_server(server))

    async def _start_tcp_server(self, server):
        async with server:
            await server.serve_forever()

    async def handle_client(self, reader, writer):
        """
        Callback for every new server-to-server connection.
        This runs concurrently for every connected peer.
        """
        addr = writer.get_extra_info('peername')
        logging.info(f"New connection from {addr}")

        try:
            while True:
                # Read data (up to 1024 bytes)
                data = await reader.read(1024)
                if not data:
                    break  # Connection closed by peer

                message = data.decode().strip()
                logging.debug(f"[{addr}] Received: {message}")

                # Optional: Send an acknowledgement (ACK) back
                response = f"ACK: {message[0:100]}"
                writer.write(response.encode())
                await writer.drain()

                try:
                    response = Socket.parse_to_data(data)
                except json.decoder.JSONDecodeError:
                    logging.error(f"Could not parse data: {data}")
                    continue
                if response is None:
                    logging.error(f"Message is Empty form {addr}")
                    continue
                await self.message_queue.put((response, addr))

        except ConnectionResetError:
            (logging.info(f"TCP-Connection reset by {addr}"))
        finally:
            writer.close()
            await writer.wait_closed()

    async def send_tcp_message(self, message: AbstractData, addr: tuple[str, int]) -> bool:
        """
        Connects to a peer, sends a message, waits for ACK, and closes.
        """
        try:
            # Establish connection
            reader, writer = await asyncio.open_connection(addr[0], addr[1])

            logging.debug(f"Sending TCP {message} to {addr[0]}:{addr[1]}")
            writer.write(str.encode(Socket.to_json(message)))
            await writer.drain()

            # Wait for the ACK
            data = await reader.read(100)

            decoded_data = data.decode()

            if data is None or not decoded_data.startswith("ACK:"):
                raise ConnectionRefusedError("Invalid ACK response")

            # Close the connection
            writer.close()
            await writer.wait_closed()

        except ConnectionRefusedError as e:
            logging.warning(f"Connection refused from other server {e}")
            return False
        return True

    async def _socket_receive_loop(self, sock: Socket, message_type: str):
        """Dedicated receive loop for a single socket."""
        loop = asyncio.get_event_loop()
        handler = self._handlers.get(message_type)

        while self._running:
            try:
                # Run blocking receive in executor
                data, addr = await loop.run_in_executor(None, sock.receive_data)
                if data and handler:
                    await handler(data, addr)
            except ConnectionResetError as e:
                logging.error("ConnectionResetError: %s", e)
            except Exception as e:
                logging.error("Error in socket receive loop: %s", e)
                break

        # old blocking implementation
        # while True:
        #     with self._lock:
        #         current_sockets = list(self.sockets.keys())
        #
        #     if not current_sockets:
        #         continue
        #
        #     readable, _, _ = select.select(current_sockets, [], [], 1.0)
        #     for sock in readable:
        #         try:
        #             data, addr = sock.receive_data()
        #         except ConnectionResetError as e:
        #             logging.error("ConnectionResetError while receiving data: %s", e)
        #             continue
        #         if data is None:
        #             continue
        #         message_type = self.sockets.get(sock)
        #         handler = self._handlers.get(message_type)
        #         if handler:
        #             handler(data, addr)  # noqa

    async def _process_outgoing_messages(self):
        """Process outgoing multicast messages from queue."""
        while self._running:
            try:
                data, addr = await self.outgoing_multicast_queue.get()
                self._send_multicast_internal(data, addr)
            except Exception as e:
                logging.error("Error processing outgoing message: %s", e)

    def send_multicast(self, data: AbstractMulticastData, addr: tuple[str, int]):
        """Thread-safe method to queue multicast messages."""
        try:
            self.outgoing_multicast_queue.put_nowait((data, addr))
        except asyncio.QueueFull:
            logging.error("Outgoing multicast queue is full!")
        return
        # was a version that worked be suddently not anymore
        # any_socket = Socket()
        # MULTICAST_TTL = 2
        # any_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        # any_socket.send_data(data, addr)
        # any_socket.close()

    def _send_multicast_internal(self, data: AbstractMulticastData, addr: tuple[str, int]):
        """Internal method that actually sends the multicast message."""
        data.sender_uuid = self.server_id
        data.sequence_number = self.current_sequence_number
        self.current_sequence_number += 1
        self.sender_cache[data.sequence_number] = data

        self.multicast_socket.send_data(data, addr)

    def _send_nack_request(self, nack_request: AbstractMulticastData, addr: tuple[str, int]):
        nack_request.sender_uuid = self.server_id
        nack_request.sequence_number = -1  # NACK requests do not need a sequence number

        any_socket = next(iter(self.sockets.keys()))
        any_socket.send_data(nack_request, addr)

    async def _handle_broadcast_message(self, data: AbstractData, addr):
        await self.message_queue.put((data, addr))

    async def _handle_unicast_message(self, data: AbstractData, addr):
        # process unicast message
        if isinstance(data, MulticastMsgRequest):
            self._handle_nack_request(data, addr)
        elif isinstance(data, AbstractMulticastData):
            await self._handle_multicast_message(data, addr)
        else:
            await self.message_queue.put((data, addr))

    async def _handle_multicast_message(self, data: AbstractMulticastData, addr):
        if data.sender_uuid == self.server_id:
            return  # ignore own messages
        self._handle_new_server(data)
        expected_seq_num = self.server_sequence_numbers.get(data.sender_uuid, -1) + 1
        # received old message
        if data.sequence_number < expected_seq_num:
            logging.debug("Discarding old multicast message with seq num %d from %s", data.sequence_number,
                          data.sender_uuid)
            return  # discard old message
        # received expected message -> can be delivered
        elif expected_seq_num == data.sequence_number:
            await self._deliver_multicast_msg(data, addr)
            # check if queued messages can now be delivered
            queue = self.server_queues.get(data.sender_uuid)
            while not queue.empty():
                current_expected = self.server_sequence_numbers.get(data.sender_uuid) + 1
                item: PrioritizedItem = queue.peek()

                if item.priority != current_expected:
                    logging.debug("Queue head seq %d != expected %d, stopping delivery",
                                  item.priority, current_expected)
                    break
                queue.get()
                await self._deliver_multicast_msg(item.item, addr)
        # received newer message -> gap in the message arrival
        elif expected_seq_num < data.sequence_number:
            logging.warning("Queuing out-of-order multicast message with seq num %d from %s", data.sequence_number,
                            data.sender_uuid)
            queue = self.server_queues.get(data.sender_uuid)
            queue.put(data.sequence_number, data)  # noqa

            # request missing messages
            missing_ids = list(range(expected_seq_num, data.sequence_number))
            logging.debug("Requesting missing multicast messages with seq nums %s from %s", missing_ids,
                          data.sender_uuid)
            self._send_nack_request(MulticastMsgRequest(missing_ids, data.sender_uuid), addr)

    def _handle_nack_request(self, data: MulticastMsgRequest, addr: tuple[str, int]):
        logging.debug("Handling NACK request for missing seq nums %s from %s", data.requested_ids, data.sender_uuid)
        if data.sender_uuid == self.server_id:
            return  # ignore own NACK requests
        elif data.requested_server_id != self.server_id:
            return  # ignore NACK requests not meant for this server

        for seq_num in data.requested_ids:
            cached_msg = self.sender_cache.get(seq_num)
            if cached_msg:
                logging.debug("Resending missing multicast message with seq num %d to %s", seq_num, addr)
                any_socket = next(iter(self.sockets.keys()))
                any_socket.send_data(cached_msg, addr)

    async def _deliver_multicast_msg(self, data: AbstractMulticastData, addr: tuple[str, int]):
        logging.debug("Delivering multicast message with seq num %d from %s", data.sequence_number, data.sender_uuid)
        await self.message_queue.put((data, addr))
        self.server_sequence_numbers[data.sender_uuid] = data.sequence_number

    def _handle_new_server(self, data: AbstractMulticastData):
        if data.sender_uuid not in self.server_queues:
            self.add_server(data.sender_uuid, data.sequence_number - 1)

    def add_server(self, server_id: UUID, sequence_number: int = -1):
        self.server_queues[server_id] = UniquePriorityQueue()
        self.server_sequence_numbers[server_id] = sequence_number

    async def add_socket(self, sock: Socket, message_type: str):
        """Dynamically add a socket and start its receive task."""
        async with self._lock:
            if sock not in self.sockets:
                self.sockets[sock] = message_type
                if self._running:
                    self._start_socket_task(sock, message_type)
                logging.info("Socket added: %s", message_type)

    async def remove_socket(self, sock: Socket):
        """Remove a socket and cancel its receive task."""
        async with self._lock:
            if sock in self.sockets:
                del self.sockets[sock]
                if sock in self._socket_tasks:
                    self._socket_tasks[sock].cancel()
                    del self._socket_tasks[sock]
                logging.info("Socket removed")

    async def stop(self):
        """Stop all socket tasks."""
        self._running = False
        for task in self._socket_tasks.values():
            task.cancel()
        self._socket_tasks.clear()
