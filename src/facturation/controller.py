from fastapi import APIRouter, Depends
from src.facturation.service import get_cond_fac, get_element_facturation, get_escomte, get_payment_methode
from .model import CondFacResponse, Escomte, PayementMode, ElementFacturation
from typing import List
from sqlalchemy.orm import Session
from database.session import get_db

router = APIRouter(
    prefix="/facture",
    tags=["facture"]
)

@router.get("/payment-condition", response_model=PayementMode)
def read_payment_method(customer_code: str, db: Session = Depends(get_db)) -> PayementMode:

    return get_payment_methode(customer_code, db)

@router.get("/escomte", response_model=Escomte)
def read_escompte(customer_code: str, db: Session = Depends(get_db)) -> Escomte:

    return get_escomte(customer_code, db)

@router.get("/condfac", response_model=Escomte)
def read_cond_fac(customer_code: str, db: Session = Depends(get_db)) -> CondFacResponse:

    return get_cond_fac(customer_code, db)

@router.get("/element", response_model=List[ElementFacturation])
def read_element_facturation(customer_code: str, db: Session = Depends(get_db)) -> List[ElementFacturation]:

    return get_element_facturation(customer_code, db)