from typing import List
from fastapi import APIRouter

from src.articles.service import get_articles_site, search_article
from .model import ArticleInput, ArticleRequest  # Make sure ArticleRequest is defined in schemas.py


router = APIRouter(
    prefix="/articles",
   tags=["articles"]
)


@router.get("/", response_model=List[ArticleRequest])
def create_article(site_id: str) -> List[ArticleRequest]:
    input = ArticleInput(site_id=site_id)
    return get_articles_site(input)

@router.get("/search/",  response_model=List[ArticleRequest])
def search_articles(sitde_id: str, q: str) -> List[ArticleRequest]:

    return search_article(sitde_id, q=f"%{q}%")



