from typing import Optional
from pydantic import BaseModel

class ArticleRequest(BaseModel):
    item_code: str
    describtion: str
    stock: Optional[float] = 0.0
    categorie: Optional[str] = None
    base_price: Optional[float] = None

class ArticleInput(BaseModel):
    site_id: str