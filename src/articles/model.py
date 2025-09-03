from typing import Optional
from pydantic import BaseModel

class ArticleRequest(BaseModel):
    item_code: str
    describtion: str
    stock: Optional[float] = 0.0

class ArticleInput(BaseModel):
    site_id: str