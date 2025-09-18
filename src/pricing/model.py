from pydantic import BaseModel
from datetime import datetime


class PricingInput(BaseModel):
    customer_code: str
    item_code: str
    quantity: str
    currency: str
    unit_of_measure: str
    order_date: datetime = datetime.now()