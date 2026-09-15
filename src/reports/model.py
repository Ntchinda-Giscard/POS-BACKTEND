from typing import Dict, List, Optional
from pydantic import BaseModel


class Kpi(BaseModel):
    revenue: float = 0.0            # sum of payments (TTC)
    transactions: int = 0
    average_basket: float = 0.0
    cash_total: float = 0.0
    card_total: float = 0.0
    digital_total: float = 0.0
    items_sold: float = 0.0
    orders_revenue_ht: float = 0.0  # from SORDER lines of the paid orders
    tax_total: float = 0.0
    previous_revenue: float = 0.0   # same length period just before, for comparison
    previous_transactions: int = 0
    revenue_change_pct: Optional[float] = None


class DayPoint(BaseModel):
    date: str
    label: str
    revenue: float = 0.0
    transactions: int = 0


class MethodPoint(BaseModel):
    method: str
    label: str
    total: float = 0.0
    count: int = 0


class ProductPoint(BaseModel):
    item_code: str
    description: str
    quantity: float = 0.0
    revenue_ht: float = 0.0
    revenue_ttc: float = 0.0


class UserPoint(BaseModel):
    user_code: str
    name: Optional[str] = None
    transactions: int = 0
    revenue: float = 0.0


class HourPoint(BaseModel):
    hour: int
    transactions: int = 0
    revenue: float = 0.0


class X3OrdersSummary(BaseModel):
    """Historical orders already in Sage X3 for the site (context, not till revenue)."""
    orders: int = 0
    revenue_ttc: float = 0.0
    revenue_ht: float = 0.0
    first_date: Optional[str] = None
    last_date: Optional[str] = None
    by_month: List[DayPoint] = []
    top_products: List[ProductPoint] = []
    top_customers: List[UserPoint] = []


class ReportSummary(BaseModel):
    date_from: str
    date_to: str
    site: Optional[str] = None
    currency: Optional[str] = None
    kpi: Kpi
    by_day: List[DayPoint] = []
    by_method: List[MethodPoint] = []
    by_user: List[UserPoint] = []
    by_hour: List[HourPoint] = []
    top_products: List[ProductPoint] = []
    cash_sessions: int = 0
    cash_difference_total: float = 0.0
    x3: X3OrdersSummary = X3OrdersSummary()
