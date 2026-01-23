import logging
from typing import Dict

from request.AbstractData.AuctionData import AuctionData
from request.AbstractData.PlaceAuctionData import PlaceAuctionData
from request.AbstractData.RetrieveAuctionsResponse import RetrieveAuctionsResponse


class AuctionManager:
    def __init__(self):
        # auction_id -> Auction
        self.auctions: Dict[int, AuctionData] = {1: AuctionData(1, "Vintage Clock", 100.0, 50.0, None, "owner1"), }

    def add_auction(self, auction: PlaceAuctionData):
        auction_id = max(self.auctions.keys()) + 1
        self.auctions[auction_id] = AuctionData(auction_id, auction.title, auction.starting_bid,
                                                auction.starting_bid, None, auction.auction_owner)
        logging.info(f"Auction added: {auction}")

    def handle_bid(self, auction_id: int, bid: float, bidder: str):
        if auction_id not in self.auctions:
            logging.info(f"Auction not handled by Server.")
            return
        if self.auctions[auction_id].current_price < bid:
            self.auctions[auction_id].current_price = bid
            self.auctions[auction_id].current_bidder = bidder
            logging.info(f"Auction updated: {self.auctions[auction_id]}")
        else:
            logging.info(f"Bid was not high enough.")
        print(self.auctions[auction_id])

    def get_all_auctions(self) -> RetrieveAuctionsResponse:
        return RetrieveAuctionsResponse(list(self.auctions.values()))
