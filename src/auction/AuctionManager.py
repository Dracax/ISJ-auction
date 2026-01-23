import logging
from typing import Dict

from request.AbstractData.AuctionBid import AuctionBid
from request.AbstractData.AuctionBidResponse import AuctionBidResponse
from request.AbstractData.AuctionData import AuctionData
from request.AbstractData.RetrieveAuctionsResponse import RetrieveAuctionsResponse
from request.AbstractData.ServerPlaceAuction import ServerPlaceAuction


class AuctionManager:
    def __init__(self):
        # auction_id -> Auction
        self.auctions: Dict[int, AuctionData] = {}

    def add_auction(self, auction: ServerPlaceAuction):
        self.auctions[auction.auction_id] = AuctionData(auction.auction_id, auction.title, auction.starting_bid,
                                                        auction.starting_bid, None, auction.auction_owner)
        logging.info(f"Auction added: {auction}")

    def handle_bid(self, bid: AuctionBid) -> AuctionBidResponse:
        if bid.auction_id not in self.auctions:
            logging.warning(f"Auction ID {bid.auction_id} not found.")
            return AuctionBidResponse(False, bid.bid_id, "Auction not found.")
        if self.auctions[bid.auction_id].current_price < bid.bid:
            self.auctions[bid.auction_id].current_price = bid.bid
            self.auctions[bid.auction_id].current_bidder = bid.name
            logging.info(f"Auction updated: {self.auctions[bid.auction_id]}")
            return AuctionBidResponse(True, bid.bid_id, "Bid accepted.")
        else:
            logging.info(
                f"Bid was not high enough. Current price: {self.auctions[bid.auction_id].current_price}, Bid: {bid.bid}")
            return AuctionBidResponse(False, bid.bid_id, "Bid too low.")

    def get_all_auctions(self) -> RetrieveAuctionsResponse:
        return RetrieveAuctionsResponse(list(self.auctions.values()))

    def get_next_auction_id(self) -> int:
        if not self.auctions:
            return 1
        return max(self.auctions.keys()) + 1
