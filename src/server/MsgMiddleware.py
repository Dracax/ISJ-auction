# TODO: Listen for all Messages (uni, multi, broad)
import logging
import threading

import select


class MsgMiddleware(threading.Thread):
    def __init__(self, server_instance):
        super(MsgMiddleware, self).__init__()
        self.server = server_instance
        self._lock = threading.Lock()

        self.sockets = [self.server.broadcast_socket, self.server.unicast_socket]

    def run(self):
        logging.info("Starting MsgMiddleware")
        while True:
            with self._lock:
                current_sockets = list(self.sockets)

            if not current_sockets:
                continue

            readable, _, _ = select.select(current_sockets, [], [], 1.0)
            for sock in readable:
                data, addr = sock.receive_data()
                if data is None:
                    continue
                if sock == self.server.broadcast_socket:
                    self.handle_broadcast_message(data, addr)
                elif sock == self.server.unicast_socket:
                    self.handle_unicast_message(data, addr)

    def handle_broadcast_message(self, data, addr):
        self.server.receive_message(data, addr)
        # check if leader

    def handle_unicast_message(self, data, addr):
        self.server.receive_message(data, addr)
        # process unicast message

    def handle_multicast_message(self, data, addr):
        pass
        # process multicast message

    def add_socket(self, sock):
        """Fügt einen Socket dynamisch hinzu."""
        with self._lock:
            if sock not in self.sockets:
                self.sockets.append(sock)
                logging.info(f"Socket hinzugefügt:")

    def remove_socket(self, sock):
        """Entfernt einen Socket."""
        with self._lock:
            if sock in self.sockets:
                self.sockets.remove(sock)

    def listen_for_message(self, data):
        pass
        # start as thread
        # All on the same port, but individual sockets
        # socket uni listen_socket.receive_data()
        # socket multi listen_socket.receive_data()
        # socket broad listen_socket.receive_data()
        # check Data for correctness etc etc

        # myServer.receive_message(data.abstractDataMessage)
