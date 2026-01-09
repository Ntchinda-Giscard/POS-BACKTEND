from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database.session import get_db
from src.articles.service import get_articles_site, search_article
from .model import ArticleInput, ArticleRequest  # Make sure ArticleRequest is defined in schemas.py


router = APIRouter(
    prefix="/articles",
   tags=["articles"]
)


@router.get("/", response_model=List[ArticleRequest])
def create_article(site_id: str, db: Session = Depends(get_db)) -> List[ArticleRequest]:
    input = ArticleInput(site_id=site_id)
    return get_articles_site(input, db)

@router.get("/search",  response_model=List[ArticleRequest])
def search_articles(sitde_id: str, q: Optional[str]=None, db: Session = Depends(get_db)) -> List[ArticleRequest]:
    query = "" if q == None else q 

    return search_article(sitde_id, q=f"%{query}%", db=db)


