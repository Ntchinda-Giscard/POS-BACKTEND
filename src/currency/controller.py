from fastapi import APIRouter
from src.currency.service import get_commande_currrency
from .model import CurrencyResponse

router = APIRouter(
    prefix="/currency",
    tags=["currency"]
)

@router.get("/code", response_model=CurrencyResponse)
def get_currency_code(customer_code: str):
    return get_commande_currrency(customer_code)