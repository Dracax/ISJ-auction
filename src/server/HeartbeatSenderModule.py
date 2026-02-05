import asyncio
import logging

from request.AbstractData.MulticastHeartbeat import MulticastHeartbeat
from request.AbstractData.MulticastHeartbeatAck import MulticastHeartbeatAck


class HeartbeatSenderModule:
    # Sends a Heartbeat message every x seconds
    HEARTBEAT_INTERVAL = 2
    # After x seconds, get 1/x missable ACK noted in server_map - 2-3* Heartbeat Interval (tolerance for network jitter, ...)->4-6sec
    TIMEOUT = 2
    # After missing this amount of ACK, consequences like removing the Server from group
    MISSABLE_ACK_THRESHOLD = 3

    def __init__(self, server):

        # Keeps track of a Server and it's missed heartbeats
        self.server = server
        self.server_map = {
            current_server.uuid: 0
            for current_server in self.server.server_group_view
        }
        self.heartbeat_round = 0
        self.expected_acks = {x.uuid for x in self.server.server_group_view if x.uuid != self.server.server_id}
        self.received_acks = set()

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
            self.check_received()
            self.received_acks = set()

    def send_heartbeat(self):
        logging.debug("Sending heartbeat #%d" % self.heartbeat_round)
        self.heartbeat_round += 1
        self.server.middleware.send_multicast(MulticastHeartbeat(self.heartbeat_round, self.server.ip, self.server.port),
                                              (self.server.MULTICAST_GROUP, self.server.multicast_port))

    def handle_ack(self, data: MulticastHeartbeatAck):
        logging.debug(f"Received ack: {data.server}")
        self.received_acks.add(data.server)

    def check_received(self):
        logging.debug("Checking received acks...")
        missing_ids = set(self.expected_acks) - set(self.received_acks)
        for server in missing_ids:
            # Increment the "missed" field
            logging.debug("Missing ack for server %d" % server)
            self.server_map[server] += 1
