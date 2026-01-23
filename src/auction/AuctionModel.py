from dataclasses import dataclass, asdict
from typing import Optional
import json
#Auction handled by leader/ one server?
@dataclass
class Auction:
    auction_id: int
    item_name: str
    current_price: float
    current_bidder: Optional[str] #Adress of Bidder, UIID of Bidder?
    client_owner: str #Right data format?

    



    



    