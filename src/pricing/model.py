from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime


class PricingInput(BaseModel):
    customer_code: str
    item_code: str
    quantity: str
    currency: str
    unit_of_measure: str
    order_date: datetime = datetime.now()


class PricingOutput(BaseModel):
    prix_brut: float
    prix_net: float
    gratuit: Optional[List[Dict[str, Any]]]=None
    total_HT: float