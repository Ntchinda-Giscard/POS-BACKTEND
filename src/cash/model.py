from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel


class OpenSessionRequest(BaseModel):
    site: str
    user_code: str
    opening_amount: float
    currency: Optional[str] = None
    notes: Optional[str] = None


class MovementRequest(BaseModel):
    type: str                 # in | out
    amount: float
    reason: Optional[str] = None
    user_code: Optional[str] = None


class CloseSessionRequest(BaseModel):
    closing_amount: float     # counted cash
    user_code: Optional[str] = None
    notes: Optional[str] = None


class MovementResponse(BaseModel):
    id: int
    type: str
    amount: float
    reason: Optional[str] = None
    user_code: Optional[str] = None
    created_at: datetime


class SessionResponse(BaseModel):
    id: int
    site: Optional[str] = None
    user_code: Optional[str] = None
    closed_by: Optional[str] = None
    opened_at: datetime
    closed_at: Optional[datetime] = None
    opening_amount: float
    cash_sales: float = 0.0
    cash_in: float = 0.0
    cash_out: float = 0.0
    expected_amount: float = 0.0
    closing_amount: Optional[float] = None
    difference: Optional[float] = None
    currency: Optional[str] = None
    status: str
    notes: Optional[str] = None
    payments_count: int = 0
    sales_by_method: Dict[str, float] = {}
    movements: List[MovementResponse] = []
