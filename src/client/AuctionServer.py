import logging
import threading
import uuid

from client.Client import Client
from request.AbstractData.AuctionBid import AuctionBid
from request.AbstractData.AuctionBidInformation import AuctionBidInformation
from request.AbstractData.AuctionBidResponse import AuctionBidResponse
from request.AbstractData.AuctionBidResponse import AuctionPlaceResponse
from request.AbstractData.AuctionData import AuctionData
from request.AbstractData.NotLeaderResponse import NotLeaderResponse
from request.AbstractData.PlaceAuctionData import PlaceAuctionData
from request.AbstractData.RetrieveAuctions import RetrieveAuctions
from request.AbstractData.RetrieveAuctionsResponse import RetrieveAuctionsResponse


class AuctionServer:
    """
    Represents an auction server that utilizes the Client class to manage auction activities.
    """

    def __init__(self):
        self.client = Client()
        self.client.start()
        threading.Thread(target=self.receive_messages, daemon=True).start()

        self.own_auctions: dict[int, PlaceAuctionData] = {}
        self.not_approved_auction: PlaceAuctionData | None = None

    def retrieve_auctions(self, open_only: bool = True) -> list[AuctionData]:
        """
        Retrieves a list of auctions from the client.

        :param open_only: If True, retrieves only open auctions.
        :return: List of auctions.
        """
        request = RetrieveAuctions(self.client.address, self.client.client_id)

        self.client.client_socket.send_data(request, self.client.server_to_talk_to)
        msg = self.client.receive_only(timeout=3)
        resend = False
        if msg:
            resend = self.handle_messages(msg)
            if resend:
                print('Unknown leader')
                self.retrieve_auctions()
        else:
            print('No response. Resending request.')
            self.client.client_socket.send_data(request, self.client.server_to_talk_to)
            msg_2 = self.client.receive_only(timeout=3)
            if msg_2:
                self.handle_messages(msg_2)
            else:
                print('Dynamic discovery')
                self.client._start_dynamic_discovery(self.client.get_broadcast_address(), 8000)
                self.client.client_socket.send_data(request, self.client.server_to_talk_to)
                msg_3 = self.client.receive_only(timeout=3)
                if msg_3:
                    self.handle_messages(msg_3)
                else:
                    print("Unable to reach servers.")

    def place_auction(self, title: str, starting_price: float, name: str):
        """
        Docstring for place_auction
        
        :param self: Description
        :param title: Description
        :type title: str
        :param starting_price: Description
        :type starting_price: float
        :param name: Description
        :type name: str
        """
        new_auction = PlaceAuctionData(self.client.address, title, starting_price, name, self.client.client_id, self.client.notification_address)
        self.not_approved_auction = new_auction
        self.client.client_socket.send_data(new_auction, self.client.server_to_talk_to)
        msg = self.client.receive_only(timeout=3)
        if msg:
            resend = self.handle_messages(msg)
            if resend:
                print('Unknown leader')
                self.place_auction(title, starting_price, name)
        else:
            print('No response. Resending request.')
            self.client.client_socket.send_data(new_auction, self.client.server_to_talk_to)
            msg_2 = self.client.receive_only(timeout=3)
            if msg_2:
                self.handle_messages(msg_2)
            else:
                print("Dynamic discovery")
                self.client._start_dynamic_discovery(self.client.get_broadcast_address(), 8000)
                self.client.client_socket.send_data(new_auction, self.client.server_to_talk_to)
                msg_3 = self.client.receive_only(timeout=3)
                if msg_3:
                    self.handle_messages(msg_3)
                else:
                    print("Unable to reach servers.")

    def send_bid(self, auction_id: int, amount: float, name: str):
        """
        Sends bid for auction: auction_id with amount bid to server side. 
        
        :param self: auction_id: int, bid: float
        """
        bid_uuid = uuid.uuid4()
        bid = AuctionBid(self.client.address, self.client.client_id, bid_uuid, auction_id, amount, name, self.client.notification_address)
        self.client.client_socket.send_data(bid, self.client.server_to_talk_to)
        logging.debug("Send Bid")
        msg = self.client.receive_only(timeout=3)
        if msg:
            resend = self.handle_messages(msg)
            if resend:
                print('Unknown leader')
                self.send_bid(auction_id, amount, name)
        else:
            print('No response. Resending request.')
            self.client.client_socket.send_data(bid, self.client.server_to_talk_to)
            msg_2 = self.client.receive_only(timeout=3)
            if msg_2:
                self.handle_messages(msg_2)
            else:
                print('Nothing received, starting Dynamic discovery')
                self.client._start_dynamic_discovery(self.client.get_broadcast_address(), 8000)
                self.client.client_socket.send_data(bid, self.client.server_to_talk_to)
                msg_3 = self.client.receive_only(timeout=3)
                if msg_3:
                    self.handle_messages(msg_3)
                else:
                    print("Unable to reach servers.")

    # def subscribe_2_auction(self, auction_id: int):
    #    sub = SubscribeAuction(self.client.address, auction_id, self.client.client_id)
    #    self.client.client_socket.send_data(sub, self.client.server_to_talk_to)

    def receive_messages(self):
        while True:
            data, _addr = self.client.incoming_msg_queue.get()
            if data:
                self.handle_messages(data)

    # Where do we place receive function?
    def handle_messages(self, response):
        if isinstance(response, AuctionBidResponse):
            if response.success:
                print(response.message)
                return False
            else:
                print(f"Bid {response.name} rejected: {response.message}")
                return False
        elif isinstance(response, RetrieveAuctionsResponse):
            print('Currently ongoing auctions:') if response.auctions else print('No ongoing auctions.')
            for auction in response.auctions:
                print(f"Auction_Id: {auction['auction_id']}, Item: {auction['item_name']}, Current Price: {auction['current_price']}")
            return False
        elif isinstance(response, NotLeaderResponse):
            print("Path taken")
            self.client.server_to_talk_to = response.leader_address
            return True
        elif isinstance(response, AuctionPlaceResponse):
            print(response.message)
            if response.success and self.not_approved_auction is not None:
                self.own_auctions[response.auction_id] = self.not_approved_auction
                self.not_approved_auction = None
            return False
        elif isinstance(response, AuctionBidInformation):
            if response.outbid:
                print(
                    f"You have been outbid on auction {response.name}! New bid: {response.bid_amount} by {response.bidder}")
            else:
                print(f"New bid on auction {response.name}: {response.bid_amount} by {response.bidder}")
            return
        else:
            print('Unknown return message.')
            return False
