from fastapi import APIRouter
from src.facturation.service import get_escomte, get_payment_methode
from .model import Escomte, PayementMode

router = APIRouter(
    prefix="/facture",
    tags=["facture"]
)

@router.get("/payment-condition", response_model=PayementMode)
def read_payment_method(customer_code: str) -> PayementMode:

    return get_payment_methode(customer_code)

@router.get("/escomte", response_model=Escomte)
def read_escompte(customer_code: str) -> Escomte:

    return get_escomte(customer_code)