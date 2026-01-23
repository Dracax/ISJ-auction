from auction.AuctionManager import AuctionManager
from auction.AuctionModel import Auction

if __name__ == "__main__":
    auction_1 = Auction(
            auction_id=1,
            item_name="Test",
            current_price=150.0,
            current_bidder="Isaak",
            client_owner= 'Client_1'
        )
    auction_2 = Auction(
            auction_id=2,
            item_name="Test2",
            current_price= 155.0,
            current_bidder= None,
            client_owner = 'Client_2'
        )
    handler_test = AuctionManager()
    handler_test.add_auction(auction_1)
    handler_test.add_auction(auction_2)
    handler_test.handle_bid(1,10,"QWERTZ")
    handler_test.handle_bid(1,100000,"MLNOP")