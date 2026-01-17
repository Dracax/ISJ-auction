# TODO: Listen for all Messages (uni, multi, broad)
import logging
import threading
from dataclasses import field, dataclass
from queue import PriorityQueue, Queue
from uuid import UUID

import select

from Socket import Socket
from request.AbstractData.AbstractData import AbstractData
from request.AbstractData.AbstractMulticastData import AbstractMulticastData


@dataclass(order=True)
class PrioritizedItem:
    priority: int
    item: AbstractMulticastData = field(compare=False)


class MsgMiddleware(threading.Thread):
    def __init__(self, server_id: UUID, sockets: dict[Socket, str]):
        super(MsgMiddleware, self).__init__()
        self.server_id = server_id
        self.sockets = sockets
        self._lock = threading.Lock()

        self._handlers = {
            'broadcast': self._handle_broadcast_message,
            'unicast': self._handle_unicast_message,
            'multicast': self._handle_multicast_message
        }

        # Queue for thread communication
        self.message_queue: Queue[tuple[AbstractData, tuple[str, int]]] = Queue()

        # testing
        self.msg_ids = [2, 1, 4, 3, 0]

        # multicast variables
        self.current_sequence_number = 0
        self.server_sequence_numbers: dict[UUID, int] = {}

        self.sender_cache: dict[int, tuple[AbstractMulticastData, tuple[str, int]]] = {}
        self.server_queues: dict[UUID, PriorityQueue] = {}

    def run(self):
        logging.info("Starting MsgMiddleware")
        while True:
            with self._lock:
                current_sockets = list(self.sockets.keys())

            if not current_sockets:
                continue

            readable, _, _ = select.select(current_sockets, [], [], 1.0)
            for sock in readable:
                data, addr = sock.receive_data()
                if data is None:
                    continue
                message_type = self.sockets.get(sock)
                handler = self._handlers.get(message_type)
                if handler:
                    handler(data, addr)  # noqa

    def send_multicast(self, data: AbstractMulticastData, addr: tuple[str, int]):
        data.sender_uuid = self.server_id
        data.sequence_number = self.current_sequence_number
        self.current_sequence_number += 1

        any_socket = next(iter(self.sockets.keys()))
        any_socket.send_data(data, addr)

    def _handle_broadcast_message(self, data, addr):
        self.message_queue.put((data, addr))
        # self.message_handler(data, addr)
        # check if leader

    def _handle_unicast_message(self, data, addr):
        # process unicast message
        pass

    def _handle_multicast_message(self, data: AbstractMulticastData, addr):
        if data.sender_uuid == self.server_id:
            return  # ignore own messages
        expected_seq_num = self.server_sequence_numbers.get(data.sender_uuid, -2) + 1
        # received old message
        if data.sequence_number < expected_seq_num:
            logging.debug("Discarding old multicast message with seq num %d from %s", data.sequence_number, data.sender_uuid)
            return  # discard old message
        # received expected message -> can be delivered
        elif expected_seq_num == data.sequence_number:
            self._deliver_multicast_msg(data, addr)
            expected_seq_num += + 1
            # check if queued messages can now be delivered
            queue = self.server_queues.get(data.sender_uuid)
            while not queue.empty():
                item: PrioritizedItem = queue.get()
                if item.priority != expected_seq_num:
                    queue.put(item)  # noqa
                    break
                self._deliver_multicast_msg(item.item, addr)
                expected_seq_num += + 1
        # received newer message -> gap in the message arrival
        elif expected_seq_num < data.sequence_number:
            logging.debug("Queuing out-of-order multicast message with seq num %d from %s", data.sequence_number, data.sender_uuid)
            queue = self.server_queues.get(data.sender_uuid)
            queue.put(PrioritizedItem(data.sequence_number, data))  # noqa

            # request missing messages

    def _deliver_multicast_msg(self, data: AbstractMulticastData, addr: tuple[str, int]):
        logging.debug("Delivering multicast message with seq num %d from %s", data.sequence_number, data.sender_uuid)
        self.message_queue.put((data, addr))
        self.server_sequence_numbers[data.sender_uuid] = data.sequence_number

    def add_server(self, server_id: UUID):
        self.server_queues[server_id] = PriorityQueue()
        self.server_sequence_numbers[server_id] = -1

    def add_socket(self, sock: Socket, message_type: str):
        """Fügt einen Socket dynamisch hinzu."""
        with self._lock:
            if sock not in self.sockets:
                self.sockets[sock] = message_type
                logging.info("Socket hinzugefügt:")

    def remove_socket(self, sock):
        """Entfernt einen Socket."""
        with self._lock:
            if sock in self.sockets:
                del self.sockets[sock]
                logging.info("Socket entfernt:")

    def listen_for_message(self, data):
        pass
        # start as thread
        # All on the same port, but individual sockets
        # socket uni listen_socket.receive_data()
        # socket multi listen_socket.receive_data()
        # socket broad listen_socket.receive_data()
        # check Data for correctness etc etc

        # myServer.receive_message(data.abstractDataMessage)
