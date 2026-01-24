import logging

import uuid
from request.AbstractData.AuctionData import AuctionData
from client.Client import Client
from request.AuctionRetrieveRequest import AuctionRetrieveRequest
from request.AbstractData.RetrieveAuctions import RetrieveAuctions
from request.AbstractData.AuctionBid import AuctionBid
from request.AbstractData.PlaceAuctionData import PlaceAuctionData
from request.AbstractData.SubscribeAuction import SubscribeAuction
from request.AbstractData.AuctionBidResponse import AuctionBidResponse
from request.AbstractData.RetrieveAuctionsResponse import RetrieveAuctionsResponse

class AuctionServer:
    """
    Represents an auction server that utilizes the Client class to manage auction activities.
    """

    def __init__(self):
        self.client = Client()
        self.client.start()

    def retrieve_auctions(self, open_only: bool = True) -> list[AuctionData]:
        """
        Retrieves a list of auctions from the client.

        :param open_only: If True, retrieves only open auctions.
        :return: List of auctions.
        """
        request = RetrieveAuctions(self.client.address, self.client.client_id)

        self.client.client_socket.send_data(request, self.client.server_to_talk_to)
        msg = self.client.receive_only(timeout=20)
        if msg:
            print("Got:", msg)
        else:
            print("Nothing received")


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
        new_auction = PlaceAuctionData(self.client.address, title, starting_price, name, self.client.client_id)
        self.client.client_socket.send_data(new_auction, self.client.server_to_talk_to)
        msg = self.client.receive_only(timeout=20)
        if msg:
            print("Got:", msg)
        else:
            print("Nothing received")
        

    def send_bid(self, auction_id: int, amount : float, name: str):
        """
        Sends bid for auction: auction_id with amount bid to server side. 
        
        :param self: auction_id: int, bid: float
        """
        bid_uuid = uuid.uuid4()
        bid = AuctionBid(self.client.address, self.client.client_id, bid_uuid, auction_id, amount, name)
        self.client.client_socket.send_data(bid, self.client.server_to_talk_to)
        logging.debug("Send Bid")
        msg = self.client.receive_only(timeout=20)
        if msg:
            self.handle_messages(msg)
        else:
            print("Nothing received")
    
    def subscribe_2_auction(self, auction_id: int):
        sub = SubscribeAuction(self.client.address, auction_id, self.client.client_id)
        self.client.client_socket.send_data(sub, self.client.server_to_talk_to)
    
    #Where do we place receive function?
    def handle_messages(self, response):
        if isinstance(response, AuctionBidResponse):
            if response.success:
                print(response.message)
            else:
                print(f"Bid {response.bid_id} rejected: {response.message}")
        if isinstance(response, RetrieveAuctionsResponse):
            print(response.auctions)
        else:
            print('Implement this.')

