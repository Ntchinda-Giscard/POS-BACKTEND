from typing import List, Optional
from pydantic import BaseModel

class ArticleRequest(BaseModel):
    item_code: str
    describtion: str
    unit_sales: str
    stock: Optional[float] = 0.0
    categorie: Optional[str] = None
    image: Optional[str] = None
    base_price: Optional[float] = None
    barcode: Optional[str] = None        # ITMMASTER.EANCOD_0
    tax_level: Optional[str] = None      # ITMMASTER.VACITM_0
    safety_stock: Optional[float] = None # ITMFACILIT.SAFSTO_0
    max_stock: Optional[float] = None    # ITMFACILIT.MAXSTO_0

class ArticleInput(BaseModel):
    site_id: str


class StockLot(BaseModel):
    lot: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    quantity: float
    allocated: float = 0.0
    received_at: Optional[str] = None


class StockItem(BaseModel):
    item_code: str
    description: str
    category: Optional[str] = None
    unit: Optional[str] = None
    barcode: Optional[str] = None
    quantity: float                      # SUM(STOCK.QTYSTUACT_0)
    allocated: float = 0.0               # SUM(STOCK.CUMALLQTY_0)
    available: float = 0.0               # quantity - allocated
    safety_stock: float = 0.0            # ITMFACILIT.SAFSTO_0
    max_stock: float = 0.0               # ITMFACILIT.MAXSTO_0
    reorder_qty: float = 0.0             # ITMFACILIT.REOMINQTY_0
    status: str = "ok"                   # out | low | ok | over
    lots: List[StockLot] = []
