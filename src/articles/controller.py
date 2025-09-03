from typing import List
from fastapi import APIRouter

from src.articles.service import get_articles_site
from .model import ArticleInput, ArticleRequest  # Make sure ArticleRequest is defined in schemas.py


router = APIRouter(
    prefix="/articles",
   tags=["articles"]
)


@router.post("/", response_model=List[ArticleRequest])
def create_article(input: ArticleInput) -> List[ArticleRequest]:
    articlel_site_stock = get_articles_site(input)
    return articlel_site_stock
