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

    def auction_to_json(auction: Auction) -> str:
        return json.dumps(asdict(auction))
    
    def json_to_auction(json_string: str) -> Auction:
        data = json.loads(json_string)
        return Auction(**data)

    



    



    