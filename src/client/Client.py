import logging
import socket
import threading
import uuid
from queue import Queue

import logging_config
from AbstractClientOrServer import AbstractClientOrServer
from Socket import Socket
from request.AbstractData.AbstractData import AbstractData
from request.AbstractData.BroadcastAnnounceRequest import BroadcastAnnounceRequest
from request.AbstractData.BroadcastAnnounceResponse import BroadcastAnnounceResponse


class Client(threading.Thread, AbstractClientOrServer):
    def __init__(self):
        super(Client, self).__init__()

        self.client_socket: Socket | None = None
        self.notification_socket: Socket | None = None
        # Socket not used for sending/ listening.
        self.send_socket: Socket = None

        self.host = socket.gethostname()
        self.ip = self.get_local_ip()

        self.server_list: list[tuple[str, int]] = []
        self.server_to_talk_to: tuple[str, int] | None = None

        self.incoming_msg_queue: Queue[tuple[AbstractData, tuple[str, int]]] = Queue()
        self.client_id = uuid.uuid4()

    def run(self):
        logging_config.setup_logging(logging.ERROR)
        # logging.info("Starting client process with PID %d", self.pid)
        self.client_socket = Socket()
        self.client_socket.bind((self.ip, 0))

        self.notification_socket = Socket()
        self.notification_socket.bind((self.ip, 0))

        self.send_socket = Socket()

        self.port = self.client_socket.getsockname()[1]
        self.address = (self.ip, self.port)
        self.notification_address = (self.ip, self.notification_socket.getsockname()[1])
        logging.info(f"Client bound to {self.ip}:{self.port}")

        thread = threading.Thread(target=self._start_dynamic_discovery, args=(self.get_broadcast_address(), 8000),
                                  daemon=True)
        thread.start()
        threading.Thread(target=self.wait_for_notifications, daemon=True).start()
        thread.join()

    def _start_dynamic_discovery(self, ip, port):
        logging.debug("Starting broadcast sender")

        broadcast_socket = self.create_broadcast_socket()

        broadcast_socket.bind((self.ip, 0))  # bind to any available port
        address = broadcast_socket.getsockname()
        message = BroadcastAnnounceRequest(address, self.host, self.ip, self.port,
                                           self.client_id)

        data = broadcast_socket.send_and_receive_data(message, (ip, port), BroadcastAnnounceResponse, timeout=5, retries=10)

        if data:
            logging.info("Received broadcast response: %s", data)
            self.server_list = list(map(tuple, data.server_addresses))
            self.server_to_talk_to = tuple(data.leader_address)

        broadcast_socket.close()

    def wait_for_notifications(self):
        while True:
            data, addr = self.notification_socket.receive_data()
            logging.info("Received notification from %s: %s", addr, data)
            self.incoming_msg_queue.put((data, addr))

    def receive_only(self, timeout: float | None = None):
        """
        Blocks until data is received on the client socket.
        Returns the deserialized object or None on timeout.
        """
        if not self.client_socket:
            logging.error("Client socket not initialized")
            return None

        if timeout is not None:
            self.client_socket.settimeout(timeout)

        try:
            data, addr = self.client_socket.receive_data()
            logging.info("Received data from %s: %s", addr, data)
            return data
        except socket.timeout:
            logging.warning("Receive timed out")
            return None
        except Exception as e:
            logging.error("Error while receiving data: %s", e)
        return None


if __name__ == "__main__":
    logging_config.setup_logging(logging.INFO)
    client = Client()
    client.start()
    client.join()
