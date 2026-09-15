from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.session import get_db
from src.settings.service import get_setting
from .service import get_article_by_barcode, get_articles_site, get_article_image, get_stock_site, search_article
from .model import ArticleInput, ArticleRequest, StockItem


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


@router.get("/barcode", response_model=ArticleRequest)
def read_by_barcode(site_id: str, code: str, db: Session = Depends(get_db)):
    """Exact match on EAN barcode (ITMMASTER.EANCOD_0) or item code — for scanner input."""
    article = get_article_by_barcode(site_id, code, db)
    if not article:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Aucun article pour le code {code}")
    return article


@router.get("/stock", response_model=List[StockItem])
def read_stock(site_id: str, with_lots: bool = False, db: Session = Depends(get_db)):
    """Inventory of a site: quantity, allocated, X3 safety/max thresholds, status (out/low/ok/over)."""
    threshold = float(get_setting(db, "low_stock_threshold", "10") or 0)
    return get_stock_site(site_id, db, low_threshold=threshold, with_lots=with_lots)


@router.get("/{item_code}/image")
def get_image(item_code: str, db: Session = Depends(get_db)):
    image_data = get_article_image(item_code, db)
    return {"image": image_data}
