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
        self.ip: str | None = None
        self.address: tuple[str, int] | None = None

    @staticmethod
    def get_broadcast_address() -> str:
        local_ip = AbstractClientOrServer.get_local_ip()
        network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
        return str(network.broadcast_address)

    def setup_multicast_socket(self, multicast_group, multicast_port):
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

        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(self.ip))

        return sock

    @staticmethod
    def get_local_ip():
        interfaces = socket.gethostbyname_ex(socket.gethostname())[2]
        # Filter out VirtualBox/VMware interfaces (commonly 192.168.56.x or 192.168.99.x)
        for ip in interfaces:
            if not ip.startswith('192.168.56.') and not ip.startswith('192.168.99.'):
                return ip
        return interfaces[0] if interfaces else '127.0.0.1'

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
