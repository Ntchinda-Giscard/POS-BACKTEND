from typing import List, Optional
from pydantic import BaseModel

class ClientResponse(BaseModel):
    code: str
    name: str
    cur: str
    mode_fac: str

class ClientFactureResponse(BaseModel):
    code: str


class TierResponse(BaseModel):
    code: str
    name: str


class ClientDetail(BaseModel):
    code: str
    name: str
    short_name: Optional[str] = None
    category: Optional[str] = None        # BCGCOD_0
    currency: Optional[str] = None
    payment_term: Optional[str] = None    # PTE_0
    payment_term_label: Optional[str] = None
    tax_rule: Optional[str] = None        # VACBPR_0
    price_type: Optional[str] = None      # PRITYP_0
    credit_limit: float = 0.0             # OSTAUZ_0
    credit_control: Optional[str] = None  # OSTCTL_0
    invoice_customer: Optional[str] = None
    payer: Optional[str] = None
    is_active: bool = True                # BPCSTA_0
    contact: Optional[str] = None         # CNTNAM_0
    address_lines: List[str] = []
    postal_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    orders_count: int = 0
    orders_total_ttc: float = 0.0
    last_order_date: Optional[str] = None
    payments_count: int = 0
    payments_total: float = 0.0
    last_payment_at: Optional[str] = None


class ClientOrder(BaseModel):
    order_id: str
    order_type: Optional[str] = None
    date: Optional[str] = None
    site: Optional[str] = None
    currency: Optional[str] = None
    total_ht: float = 0.0
    total_ttc: float = 0.0
    status: Optional[str] = None
    created_by: Optional[str] = None
    lines: int = 0
    paid: float = 0.0                     # sum of till payments on this order
    payment_methods: List[str] = []
    source: str = "x3"                    # x3 | pos
