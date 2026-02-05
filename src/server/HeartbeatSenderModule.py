import asyncio
import logging

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
        self.server = server
        self.server_map = {
            current_server: {
                "data": current_server,
                "missed": 0,
            }
            for current_server in self.server.server_group_view
        }
        self.heartbeat_round = 0
        self.expectedAcks = set(self.server_map)
        self.receivedAcks = set()

    """
    1. Send Heartbeat
    2. Wait for x seconds (Heartbeat Interval)
    3. Check the set of received ACKs
    3.1 If a server did not send an ACK -> Mark server
    4. Reset List of received ACKs
    4.1 GOTO 1
    """
    async def run(self):
        logging.info("Starting heartbeat sender...")
        while True:
            self.send_heartbeat()
            await asyncio.sleep(self.HEARTBEAT_INTERVAL)
            self.receivedAcks = set()

# TODO: HIER WURDE ASYNC DAZUGEPACKT, MACHT DAS OBEN MAYBE KAPUTT?
    async def send_heartbeat(self):
        logging.debug("Sending heartbeat #%d" % self.heartbeat_round)
        self.heartbeat_round += 1
        self.server.middleware.send_multicast(MulticastHeartbeat(self.heartbeat_round, self.server.ip, self.server.port),
                                       (self.server.MULTICAST_GROUP, self.server.multicast_port))

    async def handle_ack(self, data):
        logging.debug("Received ack: " + data)
        self.receivedAcks.add(data.server)

    async def check_received(self):
        logging.debug("Checking received acks...")
        missing_ids = set(self.server_map) - set(self.receivedAcks)
        for server in missing_ids:
            # Increment the "missed" field
            logging.debug("Missing ack for server #%d" % server)
            self.server_map[server]["missed"] += 1
