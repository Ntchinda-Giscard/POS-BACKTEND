from typing import Optional
from pydantic import BaseModel

class ArticleRequest(BaseModel):
    id: int
    title: str
    content: str
    author: str
    created_at: str
    updated_at: str
