import logging
import time

from request.AbstractData.MulticastHeartbeat import MulticastHeartbeat

class HeartbeatSenderModule:

    # Sends a Heartbeat message every x seconds
    HEARTBEAT_INTERVAL = 2
    # After x seconds, get 1/x missable ACK noted in server_map - 2-3* Heartbeat Interval (tolerance for network jitter, ...)->4-6sec
    TIMEOUT = 2
    # After missing this amount of ACK, consequences like removing the Server from group
    MISSABLE_ACK_THRESHOLD = 3

    def __init__(self, server):
        #threading.Thread.__init__(self, daemon=True)

        # Keeps track of a Server and it's missed heartbeats
        # server_list = list[tuple[ServerDataRepresentation, int]]
        self.server = server
        self.server_map = [(server_data, 0) for server_data in self.server.server_group_view]
        self.heartbeat_round = 0
        #self._stop_event = threading.Event()

    async def run(self):
        logging.info("Starting heartbeat sender...")
        while True:
            self.send_heartbeat()
            time.sleep(self.HEARTBEAT_INTERVAL)

    def send_heartbeat(self):
        logging.debug("Sending heartbeat #%d" % self.heartbeat_round)
        #for server in self.server_map.values():
        self.heartbeat_round += 1
        self.server.middleware.send_multicast(MulticastHeartbeat(self.heartbeat_round, self.server.ip, self.server.port),
                                       (self.server.MULTICAST_GROUP, self.server.multicast_port))
