# TODO: Listen for all Messages (uni, multi, broad)
import logging
import threading


class MsgMiddleware(threading.Thread):
    def __init__(self, server_instance):
        super(MsgMiddleware, self).__init__()
        self.server = server_instance

    def run(self):
        logging.info("Starting MsgMiddleware")
        while True:
            self.server.broadcast_socket.receive_data()

    def listen_for_message(self, data):
        pass
        # start as thread
        # All on the same port, but individual sockets
        # socket uni listen_socket.receive_data()
        # socket multi listen_socket.receive_data()
        # socket broad listen_socket.receive_data()
        # check Data for correctness etc etc

        # myServer.receive_message(data.abstractDataMessage)
