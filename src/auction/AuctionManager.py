import logging
from typing import Dict

from request.AbstractData.AuctionBid import AuctionBid
from request.AbstractData.AuctionBidResponse import AuctionBidResponse
from request.AbstractData.AuctionData import AuctionData
from request.AbstractData.PlaceAuctionData import PlaceAuctionData
from request.AbstractData.RetrieveAuctionsResponse import RetrieveAuctionsResponse


class AuctionManager:
    def __init__(self):
        # auction_id -> Auction
        self.auctions: Dict[int, AuctionData] = {1: AuctionData(1, "Vintage Clock", 100.0, 50.0, None, "owner1")}

    def add_auction(self, auction: PlaceAuctionData):
        auction_id = max(self.auctions.keys()) + 1
        self.auctions[auction_id] = AuctionData(auction_id, auction.title, auction.starting_bid,
                                                auction.starting_bid, None, auction.auction_owner)
        logging.info(f"Auction added: {auction}")

    def handle_bid(self, bid: AuctionBid) -> AuctionBidResponse:
        if bid.auction_id not in self.auctions:
            logging.warning(f"Auction ID {bid.auction_id} not found.")
            return AuctionBidResponse(bid.bid_id, False, "Auction not found.")
        if self.auctions[bid.auction_id].current_price < bid.bid:
            self.auctions[bid.auction_id].current_price = bid.bid
            self.auctions[bid.auction_id].current_bidder = bid.name
            logging.info(f"Auction updated: {self.auctions[bid.auction_id]}")
            return AuctionBidResponse(bid.bid_id, True, "Bid accepted.")
        else:
            logging.info(
                f"Bid was not high enough. Current price: {self.auctions[bid.auction_id].current_price}, Bid: {bid.bid}")
            return AuctionBidResponse(bid.bid_id, False, "Bid too low.")

    def get_all_auctions(self) -> RetrieveAuctionsResponse:
        return RetrieveAuctionsResponse(list(self.auctions.values()))
