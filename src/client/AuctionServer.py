from client.AuctionItem import AuctionItem
from client.Client import Client
from request.AuctionRetrieveRequest import AuctionRetrieveRequest


class AuctionServer:
    """
    Represents an auction server that utilizes the Client class to manage auction activities.
    """

    def __init__(self):
        self.client = Client()
        self.client.start()

    def retrieve_auctions(self, open_only: bool = True) -> list[AuctionItem]:
        """
        Retrieves a list of auctions from the client.

        :param open_only: If True, retrieves only open auctions.
        :return: List of auctions.
        """
        request = AuctionRetrieveRequest("RETRIEVE_AUCTIONS", None, only_open=open_only)

        self.client.send_get_request(request, AuctionRetrieveRequest)
