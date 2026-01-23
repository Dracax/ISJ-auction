import ipaddress
import socket
import struct
from abc import ABC

from Socket import Socket


class AbstractClientOrServer(ABC):
    def __init__(self):
        super(self).__init__()

        # should be set after binding to the socket
        self.port: int | None = None
        self.address: tuple[str, int] | None = None

    @staticmethod
    def get_broadcast_address() -> str:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
        return str(network.broadcast_address)

    @staticmethod
    def setup_multicast_socket(multicast_group, multicast_port):
        sock = Socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        IS_ALL_GROUPS = True
        if IS_ALL_GROUPS:
            # on this port, receives ALL multicast groups
            sock.bind(('', multicast_port))
        else:
            # on this port, listen ONLY to MCAST_GRP
            sock.bind((multicast_group, multicast_port))
        mreq = struct.pack("4sl", socket.inet_aton(multicast_group), socket.INADDR_ANY)

        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        return sock

    @staticmethod
    def create_broadcast_socket() -> Socket:
        broadcast_socket = Socket()
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return broadcast_socket

    @staticmethod
    def create_unicast_socket() -> Socket:
        unicast_socket = Socket()
        unicast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        return unicast_socket
