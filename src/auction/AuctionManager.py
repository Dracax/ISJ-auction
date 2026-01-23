import logging
from typing import Dict
from auction.AuctionModel import Auction



class AuctionManager:
    def __init__(self): 
        # auction_id -> Auction
        self.auctions: Dict[int, Auction] = {}
        
    def add_auction(self, auction: Auction):
        self.auctions[auction.auction_id] = auction
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


    def get_all_auctions(self):
        return list(self.auctions.values())




