from fastapi import APIRouter, Depends
from src.currency.service import get_commande_currrency
from .model import CurrencyResponse
from database.sync_data import get_db
from sqlalchemy.orm import Session


router = APIRouter(
    prefix="/currency",
    tags=["currency"]
)

@router.get("/code", response_model=CurrencyResponse)
def get_currency_code(customer_code: str, db: Session = Depends(get_db)):
    return get_commande_currrency(customer_code, db)