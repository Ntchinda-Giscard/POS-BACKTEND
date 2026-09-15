from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class PaymentRequest(BaseModel):
    orderId: str
    amount: float
    method: str                              # cash | card | digital
    amountTendered: Optional[float] = None   # cash: what the customer handed over
    reference: Optional[str] = None          # card: terminal approval ref / digital: txn id
    provider: Optional[str] = None           # digital: MOMO | OM
    phone: Optional[str] = None              # digital: payer phone number
    currency: Optional[str] = None
    customerCode: Optional[str] = None
    userCode: Optional[str] = None           # cashier (AUTILIS.USR_0)
    site: Optional[str] = None               # sales site; the open cash session of this site is attached


class PaymentResponse(BaseModel):
    transactionId: str
    orderId: str
    method: str
    amount: float
    amountTendered: Optional[float] = None
    change: Optional[float] = None
    reference: Optional[str] = None
    provider: Optional[str] = None
    phone: Optional[str] = None
    currency: Optional[str] = None
    customerCode: Optional[str] = None
    customerName: Optional[str] = None
    userCode: Optional[str] = None
    cashSessionId: Optional[int] = None
    site: Optional[str] = None
    status: str
    createdAt: datetime


class PaymentLine(BaseModel):
    """Order line behind a payment (SORDERP + SORDERQ)."""
    line: int
    item_code: str
    description: str
    quantity: float
    unit: Optional[str] = None
    gross_price: float
    net_price_ht: float
    net_price_ttc: float
    tax_code: Optional[str] = None
    free: bool = False


class PaymentDetail(PaymentResponse):
    lines: List[PaymentLine] = []
    total_ht: Optional[float] = None
    total_ttc: Optional[float] = None
    order_date: Optional[str] = None
