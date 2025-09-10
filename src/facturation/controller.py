from fastapi import APIRouter
from src.facturation.service import get_payment_methode
from .model import PayementMode

router = APIRouter(
    prefix="/facture",
    tags=["facture"]
)

@router.get("/payment-method", response_model=PayementMode)
def read_payment_method(customer_code: str) -> PayementMode:

    return get_payment_methode(customer_code)