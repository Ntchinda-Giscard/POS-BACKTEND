from typing import Optional
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
    gratuit: Optional[str]=None
    qty_grat: Optional[str]=None
    total_HT: float